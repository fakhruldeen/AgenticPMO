import os
import json
import re
from typing import Dict, Any, List
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pmoskills import pmoskills
from graph.state import PMOState

# Retrieve the system prompt from SDK or fallback to standard prompt
orchestrator_prompt_ref = pmoskills.get_system_prompt("pmo-orchestrator")
ORCHESTRATOR_SYSTEM_PROMPT = orchestrator_prompt_ref["prompt"] if orchestrator_prompt_ref else (
    "You are the PMOSkills Master PMO Orchestrator. Analyze the user request, "
    "identify the correct PMBOK 8 skill to activate, and update the active_skill."
)

def get_llm():
    if os.getenv("GEMINI_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    elif os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4-turbo", temperature=0)
    return None

async def orchestrator_node(state: PMOState) -> Dict[str, Any]:
    print("[AgenticPMO] Orchestrator node executing...")
    
    # Check if last message is an AI message requesting inputs (avoid loops)
    if state.get("messages") and (
        isinstance(state["messages"][-1], AIMessage) or
        (hasattr(state["messages"][-1], "type") and state["messages"][-1].type == "ai")
    ) and state.get("missing_inputs"):
        print("[Orchestrator] Loop detected: Waiting for user response to missing inputs.")
        return {}
    
    # 1. Extract the last user message
    last_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage) or (hasattr(msg, "type") and msg.type == "human"):
            last_msg = msg.content
            break
            
    # Parse project info from last user message and add to context
    project_context = dict(state.get("current_project_context") or {})
    
    # Simple regex parsing to help extract metadata from user inputs programmatically (e.g. for mock)
    # Aero Project, budget $120k
    name_match = re.search(r'(?:project|named)\s+([a-zA-Z0-9_\-\s]+?)(?:\s+with|\s+budget|\s+has|,|\.|$)', last_msg, re.IGNORECASE)
    if name_match:
        project_context["project_name"] = name_match.group(1).strip()
        project_context["Full name of the project"] = project_context["project_name"]
        
    budget_match = re.search(r'budget\s+(?:of\s+)?\$?([0-9,]+k?|[0-9]+)', last_msg, re.IGNORECASE)
    if budget_match:
        budget_str = budget_match.group(1).replace(",", "").lower()
        if 'k' in budget_str:
            budget_val = float(budget_str.replace('k', '')) * 1000
        else:
            budget_val = float(budget_str)
        project_context["project_budget"] = budget_val
        project_context["indicative budget"] = budget_val
        project_context["Approved Budget (indicative)"] = f"${budget_val:,.2f}"
        
    sponsor_match = re.search(r'sponsor(?:ed)?\s+(?:by\s+|is\s+)?([a-zA-Z\s]+?)(?:\s+with|\s+budget|,|\.|$)', last_msg, re.IGNORECASE)
    if sponsor_match:
        project_context["sponsor"] = sponsor_match.group(1).strip()
        project_context["sponsor_name"] = project_context["sponsor"]
        project_context["Sponsor"] = project_context["sponsor"]
        
    cost_var_match = re.search(r'cost\s+variance\s+(?:of\s+)?([0-9\.]+)%', last_msg, re.IGNORECASE)
    if cost_var_match:
        project_context["cost_variance_pct"] = float(cost_var_match.group(1))
        
    sched_var_match = re.search(r'schedule\s+variance\s+(?:of\s+)?([0-9\.]?[-+]?[0-9]+)\s*days', last_msg, re.IGNORECASE)
    if sched_var_match:
        project_context["schedule_variance_days"] = float(sched_var_match.group(1))
        
    contingency_match = re.search(r'contingency\s+spend\s+(?:of\s+)?\$?([0-9,]+)', last_msg, re.IGNORECASE)
    if contingency_match:
        project_context["contingency_spend"] = float(contingency_match.group(1).replace(",", ""))

    # 2. Check for LLM
    llm = get_llm()
    if llm:
        system_message = SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT + "\n\nProvide your analysis. If a skill from the PMOSkills registry needs to be executed, output a JSON structure: {\"active_skill\": \"SKL-XX-XX\"}. Otherwise answer normally.")
        response = await llm.ainvoke([system_message] + state["messages"])
        content = response.content
        
        active_skill = state.get("active_skill")
        try:
            json_match = re.search(r'\{.*?\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                if "active_skill" in data:
                    active_skill = data["active_skill"]
        except Exception:
            pass
            
        return {
            "messages": [AIMessage(content=content)],
            "current_project_context": project_context,
            "active_skill": active_skill,
            "missing_inputs": []
        }
    else:
        active_skill = state.get("active_skill")
        msg_lower = last_msg.lower()
        
        reply_content = ""
        if "governance" in msg_lower or "skl-01-01" in msg_lower or "establish governance" in msg_lower:
            active_skill = "SKL-01-01"
            reply_content = "[Orchestrator Mock] Request matches skill SKL-01-01: Establish PM Governance Framework. Directing workflow to the Executor Agent."
        elif "charter" in msg_lower or "skl-02-01" in msg_lower or "develop charter" in msg_lower or "pr01" in msg_lower:
            active_skill = "SKL-02-01"
            reply_content = "[Orchestrator Mock] Request matches skill SKL-02-01: Initiate Project or Phase. Directing workflow to the Executor Agent."
        else:
            if state.get("active_skill"):
                active_skill = state.get("active_skill")
                reply_content = f"[Orchestrator Mock] Resuming execution of {active_skill} with updated context."
            else:
                reply_content = "[Orchestrator Mock] Welcome to AgenticPMO. I can help you execute PMBOK 8 skills, such as establishing governance (SKL-01-01) or developing a project charter (SKL-02-01)."
                active_skill = None
            
        return {
            "messages": [AIMessage(content=reply_content)],
            "current_project_context": project_context,
            "active_skill": active_skill,
            "missing_inputs": []
        }
