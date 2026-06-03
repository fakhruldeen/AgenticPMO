# Custom Skills & Templates Extension Guide

This tutorial explains how to extend **AgenticPMO** with your organization's custom project management templates or add unsupported **PMBOK® 8th Edition** skills.

---

## 🛠️ Step-by-Step Skill Extension Process

Adding a custom skill (e.g. `SKL-99-01: Establish Communication Matrix`) requires updating the Orchestrator (to detect it), the Executor (to fill its template), and the Governor (to enforce any budget rules).

```
 1. Define Template ➔ 2. Update Orchestrator ➔ 3. Update Executor ➔ 4. Test Integration
```

---

### Step 1: Register the Custom Template & Skill

Create a custom subclass or extension of the local PMOSkills database, or define a fallback mapping in your workspace. For example, if you want the custom skill `SKL-99-01` to generate a **Communication Register** (`A99` template):

1. **Template Placeholder Definition**:
   Create a markdown file containing placeholders formatted as `[FIELD: Name]` or `{{Name}}`:
   ```markdown
   # Project Communication Matrix
   - Project: [FIELD: Project Name]
   - Sponsor: [FIELD: Sponsor Name]
   - Channel: [FIELD: Primary Communication Channel]
   ```

---

### Step 2: Update the Orchestrator Trigger (`agents/orchestrator.py`)

To ensure the system recognizes the custom request and activates the skill, update the intake routing.

#### 1. Online LLM Mode:
The Orchestrator's prompt automatically instructs the LLM to output `{"active_skill": "SKL-99-01"}` when the request aligns with communication planning.

#### 2. Offline Mode (Fallback Heuristics):
Add a keyword trigger inside the fallback block of `agents/orchestrator.py`:

```python
# Insert inside orchestrator_node fallback routing:
if "communication" in msg_lower or "matrix" in msg_lower or "skl-99-01" in msg_lower:
    active_skill = "SKL-99-01"
    reply_content = "[Orchestrator Mock] Request matches skill SKL-99-01: Establish Communication Matrix."
```

---

### Step 3: Configure the Executor Node (`agents/executor.py`)

Map the new skill ID to the custom template and declare its required fields.

1. **Artifact ID Mapping**:
   Update `get_artifact_id_for_skill` to return the new template ID:
   ```python
   if skill_id == "SKL-99-01":
       return "A99"
   ```
2. **Context Checking**:
   Register any mandatory project context variables inside the offline mock block of `executor_node`:
   ```python
   if active_skill == "SKL-99-01":
       mandatory_context_keys = ["project_name", "sponsor", "primary_communication_channel"]
   ```

---

### Step 4: Verify with an Integration Test (`tests/test_graph.py`)

Add a test case to validate the resolution loop for your new skill:

```python
async def test_custom_communication_skill():
    state = {
        "messages": [HumanMessage(content="Setup a communication matrix for Aero project with Slack channel")],
        "current_project_context": {},
        "active_skill": None,
        "missing_inputs": [],
        "generated_artifact": None,
        "escalation_level": None
    }
    
    # 1. Run turn (should pause for missing Sponsor)
    res = await pmo_graph.ainvoke(state)
    assert res["active_skill"] == "SKL-99-01"
    assert "Sponsor" in res["missing_inputs"]
    
    # 2. Supply missing Sponsor and resume
    res["messages"].append(HumanMessage(content="The sponsor is Alice"))
    final_res = await pmo_graph.ainvoke(res)
    assert final_res["missing_inputs"] == []
    assert final_res["generated_artifact"] is not None
```
Run `PYTHONPATH=. pytest tests/test_graph.py -v` to ensure compilation and logical flow.
