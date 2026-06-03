# API Reference & State Resumption

**AgenticPMO** exposes a FastAPI REST service to coordinate the multi-agent graph over stateless HTTP connections.

---

## 🔌 API Endpoints

### 1. GET `/`
Root health check returning server configuration metadata.

#### Response Payload:
```json
{
  "status": "healthy",
  "service": "AgenticPMO Orchestrator",
  "framework": "PMBOK 8th Edition",
  "llm_configured": false
}
```

---

### 2. POST `/chat`
Submits a message and runs the LangGraph state machine workflow.

#### Request Schema (`ChatRequest`):
```json
{
  "message": "User query or system command",
  "state": {
    "messages": [
      { "role": "human", "content": "Initial prompt" },
      { "role": "ai", "content": "Previous response" }
    ],
    "current_project_context": {
      "project_name": "Aero Project",
      "project_budget": 120000.0
    },
    "active_skill": "SKL-01-01",
    "missing_inputs": ["Sponsor"],
    "generated_artifact": null,
    "escalation_level": null
  },
  "current_project_context": {
    "project_name": "Aero Project"
  }
}
```

> [!NOTE]
> **State & Context Override**: Passing the `state` block allows you to resume a paused workflow. The optional `current_project_context` property in the root request is merged directly into the active graph state, allowing you to supply missing variables.

#### Response Schema (`ChatResponse`):
```json
{
  "messages": [
    { "role": "human", "content": "Establish PM governance framework for Aero project" },
    { "role": "ai", "content": "[Orchestrator Mock] Request matches skill SKL-01-01..." },
    { "role": "ai", "content": "[Executor Mock] Missing inputs for SKL-01-01: ['Sponsor']. Please provide: Sponsor." }
  ],
  "current_project_context": {
    "project_name": "Aero project",
    "project_budget": 120000.0
  },
  "active_skill": "SKL-01-01",
  "missing_inputs": ["Sponsor"],
  "generated_artifact": null,
  "escalation_level": null
}
```

---

## 🔄 Reconstructing and Resuming State (Multi-Turn)

The `/chat` route allows you to preserve the session without holding socket connections or memory logs on the server.

### Phase 1: Initial Query
Initiate the workflow to establish governance. The project name and budget are parsed, but the executor pauses because **Sponsor** is missing:

```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"message": "Establish governance for Aero Project with budget $120000"}' \
  http://127.0.0.1:8000/chat
```

#### Output state:
```json
{
  "active_skill": "SKL-01-01",
  "missing_inputs": ["Sponsor"],
  "generated_artifact": null,
  "escalation_level": null,
  "current_project_context": {
    "project_name": "Aero Project",
    "project_budget": 120000.0
  }
}
```

### Phase 2: Resume with Missing Input
Submit a second request carrying the entire returned `state` payload inside the `"state"` property and providing the sponsor name in the message:

```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{
    "message": "The project sponsor is Alice Smith",
    "state": {
      "messages": [
        {"role": "human", "content": "Establish governance for Aero Project with budget $120000"},
        {"role": "ai", "content": "[Executor Mock] Missing inputs for SKL-01-01: ['Sponsor']."}
      ],
      "current_project_context": {
        "project_name": "Aero Project",
        "project_budget": 120000.0
      },
      "active_skill": "SKL-01-01",
      "missing_inputs": ["Sponsor"],
      "generated_artifact": null,
      "escalation_level": null
    }
  }' \
  http://127.0.0.1:8000/chat
```

#### Resulting state:
The orchestrator extracts the sponsor's name, the executor interpolates the template and writes it to `artifacts/a05_aero_project.md`, and the governor classifies the variance:
```json
{
  "active_skill": "SKL-01-01",
  "missing_inputs": [],
  "generated_artifact": "<!-- Markdown Template populated with project context -->",
  "escalation_level": "T3",
  "current_project_context": {
    "project_name": "Aero Project",
    "project_budget": 120000.0,
    "sponsor": "Alice Smith"
  }
}
```
