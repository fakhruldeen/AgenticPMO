# Testing and Quality Assurance

**AgenticPMO** features a dedicated integration test suite in [tests/test_graph.py](file:///home/mohamed/Desktop/Work/AgenticPMO/AgenticPMO/tests/test_graph.py) that validates the entire multi-agent state loop, input resolution constraints, and governor escalation thresholds.

---

## 🧪 Integration Test Suite Configuration

The tests execute the compiled `StateGraph` app. They are designed to run in both **Offline Mock Mode** (default) and **Online LLM Mode** (when API keys are present in the environment).

### 🛠️ Execution Command:
Run the tests using `pytest` with the `PYTHONPATH` set to the project root:

```bash
PYTHONPATH=. pytest tests/test_graph.py -v
```

---

## 📝 Documented Test Cases

The test suite validates three core orchestration scenarios:

### 1. Happy Path Workflow (`test_graph_happy_path`)
Verifies execution when all mandatory fields are provided in the project context on the first turn.
- **Scenario**: User requests: *"Establish governance for Aero Project with budget $90000 sponsored by Alice Smith"*.
- **Checks**:
  - `active_skill` is set to `SKL-01-01`.
  - `missing_inputs` is empty `[]` because Name, Budget, and Sponsor are parsed from the prompt.
  - `generated_artifact` contains the populated markdown draft template.
  - `escalation_level` is set to `T1` (under budget limits).

### 2. Missing Inputs Paused Loop (`test_graph_missing_inputs_loop`)
Validates that the orchestrator loop detection holds the graph execution when fields are missing and resumes correctly once they are supplied.
- **Turn 1 (Initial prompt)**: User requests: *"Establish governance for Aero Project with budget $90000"*.
  - **Checks**: Executor halts. `missing_inputs` contains `["Sponsor"]`. Graph ends execution.
- **Turn 2 (State resumption)**: Re-invokes graph by passing back the serialized state and the message: *"The sponsor is Alice Smith"*.
  - **Checks**: Orchestrator extracts the sponsor, `missing_inputs` resets to `[]`, the artifact is generated, and graph successfully terminates.

### 3. Governor Escalation Thresholds (`test_governor_escalation_t3`)
Verifies that the Governor Agent flags metrics exceeding delegable tolerances and prompts sponsor alerts.
- **Scenario**: User requests: *"Establish governance for Aero Project with budget $120000 sponsored by Alice Smith"*.
- **Checks**:
  - `active_skill` resolves to `SKL-01-01`.
  - Budget ($120K) exceeds the delegated threshold of $100K.
  - `escalation_level` is elevated to `T3`.
  - State messages contain a `[Governor Alert]` warning requesting human-in-the-loop sponsor confirmation.

---

## 📴 Offline Validation vs. Online LLM Mode

The test suite uses a dual-engine architecture:

- **Offline Mode**: If `GEMINI_API_KEY` and `OPENAI_API_KEY` are unset, nodes fall back to a deterministic, regex-based parsing engine. This allows local validation and CI/CD pipelines to run instantly without third-party network dependencies.
- **Online Mode**: When API keys are configured, the graph switches to real LLM model invocations. The agent prompts the models to extract keys, build variables maps, and perform qualitative reviews on the output artifacts.
