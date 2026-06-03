import os
import re
import json
from typing import Dict, Any, Tuple, List
from langchain_core.messages import AIMessage, SystemMessage
from pmoskills import pmoskills
from graph.state import PMOState

def get_llm():
    if os.getenv("GEMINI_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    elif os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4-turbo", temperature=0)
    return None

def compute_quantitative_tier(context: Dict[str, Any]) -> Tuple[str, List[str]]:
    reasons = []
    tier = "T1"
    
    # 1. Check for T4 triggers (cross-project, strategic, portfolio level)
    cross_project = context.get("cross_project_impact") or context.get("enterprise_contention") or context.get("cross_initiative_budget_shift")
    if cross_project:
        reasons.append("Cross-initiative budget shift or enterprise resource contention detected.")
        return "T4", reasons
        
    # 2. Extract values
    budget = float(context.get("project_budget") or 0.0)
    cost_var = float(context.get("cost_variance_pct") or 0.0)
    sched_var = float(context.get("schedule_variance_days") or 0.0)
    contingency = float(context.get("contingency_spend") or 0.0)
    
    # T3 threshold overrides:
    # If budget size exceeds $100K, or cost variance > 10%, or schedule variance > 15 days, or contingency spend > $50K
    if budget > 100000:
        tier = "T3"
        reasons.append(f"Total budget ${budget:,.2f} exceeds standard $100,000 threshold.")
    if cost_var > 10:
        tier = "T3"
        reasons.append(f"Cost variance of {cost_var}% exceeds the 10% tolerance threshold.")
    if sched_var > 15:
        tier = "T3"
        reasons.append(f"Schedule variance of {sched_var} days exceeds the 15 days threshold.")
    if contingency > 50000:
        tier = "T3"
        reasons.append(f"Contingency reserve spend ${contingency:,.2f} exceeds $50,000.")
        
    if tier == "T3":
        return "T3", reasons
        
    # 3. Check for T2 triggers
    # Cost variance 5%-10%, Schedule variance 5-15 days, Contingency spend $10K-$50K
    if 5 <= cost_var <= 10:
        tier = "T2"
        reasons.append(f"Cost variance of {cost_var}% falls within T2 tolerance (5%-10%).")
    if 5 <= sched_var <= 15:
        tier = "T2"
        reasons.append(f"Schedule variance of {sched_var} days falls within T2 tolerance (5-15 days).")
    if 10000 <= contingency <= 50000:
        tier = "T2"
        reasons.append(f"Contingency spend ${contingency:,.2f} falls within T2 tolerance ($10K-$50K).")
        
    if tier == "T2":
        return "T2", reasons
        
    reasons.append("Project metrics are within T1 Operational tolerances.")
    return "T1", reasons

async def governor_node(state: PMOState) -> Dict[str, Any]:
    print("[AgenticPMO] Governor node executing...")
    
    context = state.get("current_project_context") or {}
    
    # 1. Quantitative Programmatic Audit
    prog_tier, prog_reasons = compute_quantitative_tier(context)
    
    # 2. Qualitative LLM Audit (if LLM is available)
    llm = get_llm()
    final_tier = prog_tier
    llm_reasons = []
    
    if llm and state.get("generated_artifact"):
        prompt = (
            f"You are the Governance Threshold Router auditing a project decision under PMBOK 8 rules.\n"
            f"Proposed Artifact Context:\n{state.get('generated_artifact')[:2000]}\n\n"
            f"Quantitative classification: {prog_tier} due to: {prog_reasons}\n\n"
            "Evaluate if any qualitative factors (such as contract changes, regulatory compliance, strategic alignment shifts) "
            "require elevating the decision classification band. Standard bands are:\n"
            "- T1 (Operational)\n"
            "- T2 (Controlled Change)\n"
            "- T3 (Governance Change)\n"
            "- T4 (Enterprise Portfolio)\n\n"
            "Output your audit result in JSON format:\n"
            "{\n"
            "  \"escalation_level\": \"T1|T2|T3|T4\",\n"
            "  \"rationale\": \"Description of qualitative factors\"\n"
            "}"
        )
        try:
            response = await llm.ainvoke([SystemMessage(content=prompt)])
            json_match = re.search(r'\{.*?\}', response.content, re.DOTALL)
            data = json.loads(json_match.group(0))
            qual_tier = data.get("escalation_level", "T1")
            llm_reasons.append(data.get("rationale", ""))
            
            # Map bands to numeric levels for worst-case evaluation
            band_levels = {"T1": 1, "T2": 2, "T3": 3, "T4": 4}
            if band_levels.get(qual_tier, 1) > band_levels.get(prog_tier, 1):
                final_tier = qual_tier
                print(f"[Governor] Escalating from quantitative {prog_tier} to qualitative {qual_tier}")
        except Exception as e:
            print(f"[Governor] Qualitative LLM audit failed: {e}")
            
    # Combine reasons
    all_reasons = prog_reasons + llm_reasons
    reasons_str = "\n".join(all_reasons)
    
    # Determine escalation alert message
    messages = []
    if final_tier in ["T3", "T4"]:
        alert = (
            f"[Governor Alert] Decision Band: {final_tier}.\n"
            f"Rationale:\n{reasons_str}\n\n"
            f"⚠️ HUMAN-IN-THE-LOOP SPONSOR CONFIRMATION REQUIRED: "
            f"This change exceeds delegated project tolerances (T2) and must be formally authorized by the Project Sponsor."
        )
        messages.append(AIMessage(content=alert))
    else:
        alert = f"[Governor] Decision Band: {final_tier} (Within standard project PM limits). Approved."
        messages.append(AIMessage(content=alert))
        
    return {
        "escalation_level": final_tier,
        "messages": messages
    }
