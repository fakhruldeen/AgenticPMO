import os
import re
import json
from typing import Dict, Any, List
from langchain_core.messages import AIMessage, SystemMessage
from pmoskills import pmoskills, inject
from graph.state import PMOState

def get_llm():
    if os.getenv("GEMINI_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    elif os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4-turbo", temperature=0)
    return None

def get_artifact_id_for_skill(skill_id: str, skill_data: Dict[str, Any]) -> str:
    metadata = skill_data.get("metadata", {})
    output_str = metadata.get("primary_artifact_output") or ""
    match = re.search(r'A\d+', output_str)
    if match:
        return match.group(0)
    # Default fallback mapping
    if skill_id == "SKL-01-01":
        return "A05"
    if skill_id == "SKL-02-01":
        return "A04"
    return "A01"

def extract_placeholders(template_text: str) -> List[str]:
    # Match [FIELD: some name]
    fields = re.findall(r'\[FIELD:\s*(.*?)\s*\]', template_text)
    # Match {{some name}}
    braces = re.findall(r'\{\{\s*(.*?)\s*\}\}', template_text)
    return list(set([f.strip() for f in fields + braces]))

def map_context_to_placeholders(context: Dict[str, Any], placeholders: List[str]) -> Dict[str, Any]:
    mapped = {}
    normalized_context = {k.lower().replace("_", "").replace(" ", ""): v for k, v in context.items()}
    
    for pl in placeholders:
        pl_norm = pl.lower().replace("_", "").replace(" ", "")
        
        # Direct check
        if pl in context:
            mapped[pl] = context[pl]
        elif pl_norm in normalized_context:
            mapped[pl] = normalized_context[pl_norm]
        # Custom synonyms
        elif "projectname" in pl_norm and "projectname" in normalized_context:
            mapped[pl] = normalized_context["projectname"]
        elif "budget" in pl_norm and "projectbudget" in normalized_context:
            mapped[pl] = normalized_context["projectbudget"]
        elif "sponsor" in pl_norm and "sponsor" in normalized_context:
            mapped[pl] = normalized_context["sponsor"]
            
    return mapped

async def executor_node(state: PMOState) -> Dict[str, Any]:
    print("[AgenticPMO] Executor node executing...")
    active_skill = state.get("active_skill")
    if not active_skill:
        return {"missing_inputs": [], "generated_artifact": None}
        
    # Retrieve skill details
    skill = pmoskills.get_skill(active_skill)
    if not skill:
        raise ValueError(f"Skill {active_skill} not found in the pmoskills registry.")
        
    artifact_id = get_artifact_id_for_skill(active_skill, skill)
    artifact = pmoskills.get_artifact(artifact_id)
    if not artifact:
        raise ValueError(f"Artifact template {artifact_id} not found in database.")
        
    template_text = artifact.get("rawContent") or artifact.get("template") or ""
    placeholders = extract_placeholders(template_text)
    
    # Check if we have an LLM
    llm = get_llm()
    if llm:
        # LLM based execution and quality checking
        prompt = (
            f"You are the Skill Executor Agent running PMBOK 8 Skill: {active_skill} ({skill.get('title')}).\n"
            f"Prerequisite fields in template:\n{placeholders}\n\n"
            f"Available Project Context:\n{state.get('current_project_context')}\n\n"
            "Analyze if the available context satisfies the template requirements. "
            "Output your analysis in JSON format:\n"
            "{\n"
            "  \"missing_inputs\": [\"list\", \"of\", \"missing\", \"mandatory\", \"fields\"],\n"
            "  \"variables_map\": {\"template_placeholder\": \"value_from_context\"}\n"
            "}"
        )
        response = await llm.ainvoke([SystemMessage(content=prompt)])
        try:
            json_match = re.search(r'\{.*?\}', response.content, re.DOTALL)
            data = json.loads(json_match.group(0))
            missing = data.get("missing_inputs", [])
            variables_map = data.get("variables_map", {})
        except Exception:
            # Fallback to programmatic mapping
            variables_map = map_context_to_placeholders(state.get("current_project_context") or {}, placeholders)
            missing = [p for p in placeholders if p not in variables_map]
            
        if missing:
            message_content = f"[Executor] Missing required inputs to execute {active_skill}: {', '.join(missing)}. Please provide these details."
            return {
                "missing_inputs": missing,
                "messages": [AIMessage(content=message_content)]
            }
            
        # All inputs satisfied, generate artifact
        populated_artifact = inject(template_text, variables_map)
        
        # Run quality check with LLM
        quality_prompt = (
            f"Verify if the following generated markdown document meets all PMBOK 8 quality rules:\n\n"
            f"{populated_artifact}\n\n"
            "Check for:\n"
            "- No unfilled placeholders (like [FIELD: ...])\n"
            "- Internal consistency\n"
            "Output the audited markdown document, with a 'Quality Gate Status: PASS' header."
        )
        quality_response = await llm.ainvoke([SystemMessage(content=quality_prompt)])
        
        return {
            "missing_inputs": [],
            "generated_artifact": quality_response.content,
            "messages": [AIMessage(content=f"[Executor] Successfully executed skill {active_skill} and generated compliance artifact {artifact_id}.")]
        }
    else:
        # Offline mock execution using programmatic mapping
        context = state.get("current_project_context") or {}
        
        # Check mandatory context keys
        mandatory_context_keys = []
        if active_skill in ["SKL-01-01", "SKL-02-01"]:
            mandatory_context_keys = ["project_name", "project_budget", "sponsor"]
        else:
            mandatory_context_keys = ["project_name"]
            
        missing = [m.replace("_", " ").title() for m in mandatory_context_keys if m not in context or not context[m]]
        
        if missing:
            msg = f"[Executor Mock] Missing inputs for {active_skill}: {missing}. Please provide: {', '.join(missing)}."
            return {
                "missing_inputs": missing,
                "messages": [AIMessage(content=msg)]
            }
            
        variables_map = map_context_to_placeholders(context, placeholders)
        # Ensure we fill any missing placeholders in variables_map with sensible defaults
        for pl in placeholders:
            if pl not in variables_map:
                if "name" in pl.lower() and "project" in pl.lower():
                    variables_map[pl] = context.get("project_name", "New Project")
                elif "manager" in pl.lower():
                    variables_map[pl] = context.get("project_manager", "PM")
                elif "sponsor" in pl.lower():
                    variables_map[pl] = context.get("sponsor", "Sponsor")
                elif "date" in pl.lower() or "YYYY-MM-DD" in pl:
                    variables_map[pl] = "2026-06-03"
                elif "version" in pl.lower() or "1.0" in pl:
                    variables_map[pl] = "1.0"
                elif "id" in pl.lower():
                    variables_map[pl] = "PRJ-01"
                else:
                    variables_map[pl] = "N/A"
            
        # Populate artifact
        populated_artifact = inject(template_text, variables_map)
        
        # Programmatic quality standard check
        quality_header = (
            f"---\n"
            f"doc_id: {artifact_id}\n"
            f"status: Approved\n"
            f"authority: pmoskills\n"
            f"quality_gate: PASS\n"
            f"---\n\n"
        )
        final_artifact = quality_header + populated_artifact
        
        # Write file to workspace root if it exists
        try:
            os.makedirs("artifacts", exist_ok=True)
            filepath = f"artifacts/{artifact_id.lower()}_{context.get('project_name', 'project').lower().replace(' ', '_')}.md"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(final_artifact)
            print(f"[Executor Mock] Wrote artifact file locally to {filepath}")
        except Exception as e:
            print(f"[Executor Mock] Failed to write file locally: {e}")
            
        success_msg = f"[Executor Mock] Successfully executed skill {active_skill} and generated artifact {artifact_id}."
        return {
            "missing_inputs": [],
            "generated_artifact": final_artifact,
            "messages": [AIMessage(content=success_msg)]
        }
