import os
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from graph.workflow import app as pmo_graph
from schemas.models import ChatRequest, ChatResponse, MessageItem

app = FastAPI(
    title="AgenticPMO API",
    description="Intelligence and orchestration layer for PMBOK 8th Edition project workflows.",
    version="1.0.0"
)

def serialize_messages(messages: List[Any]) -> List[MessageItem]:
    serialized = []
    for msg in messages:
        role = "system"
        if isinstance(msg, HumanMessage) or (hasattr(msg, "type") and msg.type == "human"):
            role = "human"
        elif isinstance(msg, AIMessage) or (hasattr(msg, "type") and msg.type == "ai"):
            role = "ai"
        
        # Extract content securely
        content = getattr(msg, "content", "")
        if isinstance(content, list):
            content = str(content)
            
        serialized.append(MessageItem(role=role, content=content))
    return serialized

def deserialize_messages(items: List[Dict[str, Any]]) -> List[Any]:
    deserialized = []
    for item in items:
        role = item.get("role", "human")
        content = item.get("content", "")
        if role == "human":
            deserialized.append(HumanMessage(content=content))
        elif role == "ai":
            deserialized.append(AIMessage(content=content))
        else:
            deserialized.append(SystemMessage(content=content))
    return deserialized

@app.get("/")
def get_root():
    """Health check and API metadata endpoint."""
    return {
        "status": "healthy",
        "service": "AgenticPMO Orchestrator",
        "framework": "PMBOK 8th Edition",
        "llm_configured": os.getenv("OPENAI_API_KEY") is not None or os.getenv("GEMINI_API_KEY") is not None
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Processes project management commands through the LangGraph agent network."""
    try:
        # 1. Initialize or reconstruct state
        state: Dict[str, Any] = {}
        
        if request.state:
            # Reconstruct from client-provided state
            state["current_project_context"] = request.state.get("current_project_context") or {}
            state["active_skill"] = request.state.get("active_skill")
            state["missing_inputs"] = request.state.get("missing_inputs") or []
            state["generated_artifact"] = request.state.get("generated_artifact")
            state["escalation_level"] = request.state.get("escalation_level")
            
            raw_msgs = request.state.get("messages") or []
            state["messages"] = deserialize_messages(raw_msgs)
        else:
            state["current_project_context"] = {}
            state["active_skill"] = None
            state["missing_inputs"] = []
            state["generated_artifact"] = None
            state["escalation_level"] = None
            state["messages"] = []
            
        # 2. Merge current request values
        # Append new user message
        state["messages"].append(HumanMessage(content=request.message))
        
        # Merge project context (request context overrides previous)
        if request.current_project_context:
            state["current_project_context"].update(request.current_project_context)
            
        # 3. Run the LangGraph State Machine
        final_state = await pmo_graph.ainvoke(state)
        
        # 4. Construct response payload
        return ChatResponse(
            messages=serialize_messages(final_state.get("messages", [])),
            current_project_context=final_state.get("current_project_context") or {},
            active_skill=final_state.get("active_skill"),
            missing_inputs=final_state.get("missing_inputs") or [],
            generated_artifact=final_state.get("generated_artifact"),
            escalation_level=final_state.get("escalation_level")
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")
