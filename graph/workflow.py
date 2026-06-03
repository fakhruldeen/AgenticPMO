from langgraph.graph import StateGraph, START, END
from graph.state import PMOState
from agents.orchestrator import orchestrator_node
from agents.executor import executor_node
from agents.governor import governor_node

from langchain_core.messages import AIMessage

# 1. Routing functions
def route_orchestrator(state: PMOState) -> str:
    """Decides where to route from the orchestrator node based on active_skill."""
    # If the last message is from the AI and we have missing inputs, terminate the run
    if state.get("missing_inputs") and state.get("messages") and (
        isinstance(state["messages"][-1], AIMessage) or
        (hasattr(state["messages"][-1], "type") and state["messages"][-1].type == "ai")
    ):
        return END
        
    if state.get("active_skill"):
        return "executor"
    return END

def route_executor(state: PMOState) -> str:
    """Decides where to route from the executor node based on missing inputs."""
    if state.get("missing_inputs"):
        return "orchestrator"
    return "governor"

# 2. Build the graph workflow
workflow = StateGraph(PMOState)

# Add node definitions
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("executor", executor_node)
workflow.add_node("governor", governor_node)

# Set starting point
workflow.add_edge(START, "orchestrator")

# Add conditional routing
workflow.add_conditional_edges(
    "orchestrator",
    route_orchestrator,
    {
        "executor": "executor",
        END: END
    }
)

workflow.add_conditional_edges(
    "executor",
    route_executor,
    {
        "orchestrator": "orchestrator",
        "governor": "governor"
    }
)

# Set finish connection
workflow.add_edge("governor", END)

# Compile workflow
app = workflow.compile()
