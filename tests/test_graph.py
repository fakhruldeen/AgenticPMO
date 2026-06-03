import asyncio
import pytest
from langchain_core.messages import HumanMessage
from graph.workflow import app as pmo_graph

def run_async(coro):
    """Helper to run async code inside sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)

def test_happy_path_governance_escalation():
    """Verifies that with complete inputs and budget > $100K, the skill executes and escalates to T3."""
    state = {
        "messages": [HumanMessage(content="Establish project governance framework for Aero Project with budget $120000 and sponsor Alice Smith.")],
        "current_project_context": {},
        "active_skill": None,
        "missing_inputs": [],
        "generated_artifact": None,
        "escalation_level": None
    }
    
    final_state = run_async(pmo_graph.ainvoke(state))
    
    assert final_state["active_skill"] == "SKL-01-01"
    assert not final_state["missing_inputs"]
    assert final_state["generated_artifact"] is not None
    assert "Aero Project" in final_state["generated_artifact"]
    assert final_state["escalation_level"] == "T3"

def test_missing_inputs_loop():
    """Verifies the state machine pauses and requests missing inputs, then completes when supplied."""
    # 1. Ask for governance without sponsor name
    state = {
        "messages": [HumanMessage(content="Establish governance for Aero Project with budget $50000")],
        "current_project_context": {},
        "active_skill": None,
        "missing_inputs": [],
        "generated_artifact": None,
        "escalation_level": None
    }
    
    state1 = run_async(pmo_graph.ainvoke(state))
    
    assert state1["active_skill"] == "SKL-01-01"
    assert "Sponsor" in state1["missing_inputs"]
    assert state1["generated_artifact"] is None
    
    # 2. Provide the sponsor name
    state1["messages"].append(HumanMessage(content="The project sponsor is Alice Smith"))
    
    final_state = run_async(pmo_graph.ainvoke(state1))
    
    assert final_state["active_skill"] == "SKL-01-01"
    assert not final_state["missing_inputs"]
    assert final_state["generated_artifact"] is not None
    assert "Alice Smith" in final_state["generated_artifact"]
    assert final_state["escalation_level"] == "T1"

def test_governance_escalation_rules():
    """Verifies that the Governor node accurately categorizes decision levels from T1 to T4."""
    # T1: standard project, no variances
    state_t1 = {
        "messages": [HumanMessage(content="Establish governance for Small Project with budget $20000 and sponsor Bob.")],
        "current_project_context": {},
        "active_skill": None,
        "missing_inputs": [],
        "generated_artifact": None,
        "escalation_level": None
    }
    res_t1 = run_async(pmo_graph.ainvoke(state_t1))
    assert res_t1["escalation_level"] == "T1"
    
    # T2: cost variance 8%
    state_t2 = {
        "messages": [HumanMessage(content="Establish governance for Med Project with budget $20000 and sponsor Bob.")],
        "current_project_context": {"cost_variance_pct": 8.0},
        "active_skill": None,
        "missing_inputs": [],
        "generated_artifact": None,
        "escalation_level": None
    }
    res_t2 = run_async(pmo_graph.ainvoke(state_t2))
    assert res_t2["escalation_level"] == "T2"

    # T3: cost variance 12% (>10%)
    state_t3 = {
        "messages": [HumanMessage(content="Establish governance for Large Project with budget $20000 and sponsor Bob.")],
        "current_project_context": {"cost_variance_pct": 12.0},
        "active_skill": None,
        "missing_inputs": [],
        "generated_artifact": None,
        "escalation_level": None
    }
    res_t3 = run_async(pmo_graph.ainvoke(state_t3))
    assert res_t3["escalation_level"] == "T3"

    # T4: cross project impact
    state_t4 = {
        "messages": [HumanMessage(content="Establish governance for Strat Project with budget $20000 and sponsor Bob.")],
        "current_project_context": {"cross_project_impact": True},
        "active_skill": None,
        "missing_inputs": [],
        "generated_artifact": None,
        "escalation_level": None
    }
    res_t4 = run_async(pmo_graph.ainvoke(state_t4))
    assert res_t4["escalation_level"] == "T4"
