from typing import TypedDict, List, Dict, Optional, Any, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class PMOState(TypedDict):
    """LangGraph state schema for AgenticPMO orchestrator workflow."""
    messages: Annotated[List[BaseMessage], add_messages]
    current_project_context: Dict[str, Any]
    active_skill: Optional[str]
    missing_inputs: List[str]
    generated_artifact: Optional[str]
    escalation_level: Optional[str]
