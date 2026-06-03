from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's chat input message.")
    current_project_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata key-value pairs representing the project context.")
    state: Optional[Dict[str, Any]] = Field(None, description="Optional previous graph state to resume from.")

class MessageItem(BaseModel):
    role: str = Field(..., description="Role of the message author (e.g. human, ai, system).")
    content: str = Field(..., description="Message text content.")

class ChatResponse(BaseModel):
    messages: List[MessageItem] = Field(..., description="The conversation history messages.")
    current_project_context: Dict[str, Any] = Field(..., description="The updated project context.")
    active_skill: Optional[str] = Field(None, description="The skill currently active in execution.")
    missing_inputs: List[str] = Field(default_factory=list, description="Any missing inputs required to continue execution.")
    generated_artifact: Optional[str] = Field(None, description="The generated Markdown artifact contents.")
    escalation_level: Optional[str] = Field(None, description="The governance escalation band (T1-T4).")
