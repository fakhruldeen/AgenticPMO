# Agent Roles & PMBOK Skill Registry

**AgenticPMO** implements a three-agent network. Each agent operates as a specialized node within the LangGraph workflow, executing targeted project management responsibilities based on PMBOK® 8th Edition rules.

---

## 🤖 Cooperative Agent Roles

```
  User Request
      │
      ▼
┌──────────────┐      If Context incomplete      ┌──────────────┐
│ Orchestrator │ ◄────────────────────────────── │   Executor   │
└──────┬───────┘                                 └──────┬───────┘
       │ If Context complete                            │ All inputs met,
       ▼                                                │ generate artifact
┌──────────────┐                                        ▼
│   Executor   │ ──────────────────────────────────────►┌──────────────┐
└──────────────┘                                        │   Governor   │
                                                        └──────┬───────┘
                                                               │ Run audits &
                                                               ▼ checks
                                                              [END]
```

### 1. PMO Orchestrator Agent (`agents/orchestrator.py`)
The gateway node of the agent network. It coordinates user interaction:
- **Intake Parsing**: When a request is received, it extracts key metadata variables (e.g., project name, budget, sponsor, variance values) from the user's natural language messages using helper regular expressions and adds them to `current_project_context`.
- **System Instructions**: Loads the standard PMBOK 8 master system instruction prompt (`pmo-orchestrator`) from the `pmoskills` database.
- **Skill Classification**: If an LLM (Gemini or OpenAI) is configured, the orchestrator prompts it to match the request to a specific skill in the PMOSkills registry (e.g., `SKL-01-01`). If running offline, a keyword-based fallback router maps terms like `"governance"` to `SKL-01-01` or `"charter"` to `SKL-02-01`.

### 2. Skill Executor Agent (`agents/executor.py`)
The builder node that compiles compliant project templates:
- **Registry Integration**: Fetches the PMBOK 8 skill definition and its mapped output artifact template (e.g., `A05` for `SKL-01-01`) from the `pmoskills` SDK database.
- **Context Validation**: Compiles the list of required fields from the template placeholders (e.g. `[FIELD: Sponsor Name]`) and checks if they are satisfied by the current context. If any mandatory fields (like Project Name, Budget, Sponsor) are missing, it halts execution and records them in `missing_inputs`.
- **Placeholder Injection**: Performs template interpolation using the SDK's `pmoskills.inject` tool.
- **Quality Gate Check**: Audits the completed markdown artifact. If an LLM is present, it validates the formatting and injects a `Quality Gate Status: PASS` header. Locally, it writes the completed document into the `artifacts/` folder.

### 3. Governance Router Agent (`agents/governor.py`)
The compliance audit node that enforces organization limits:
- **Quantitative Audit**: Examines the project metrics in `current_project_context` against delegated authority tolerances (aligned with PMBOK 8 standards).
- **Qualitative Audit**: If an LLM is active, the governor analyzes the actual text of the populated project charter or framework to check for external triggers (regulatory shifts, cross-project contentions) that demand escalation.
- **Sponsor Alert Trigger**: If the project falls into high-risk bands (T3 or T4), it appends a mandatory human-in-the-loop warning to prompt the project sponsor for approval.

---

## 📊 Governance Classification Bands

Project decisions are sorted into four distinct authorization tiers based on quantitative metric overrides:

| Tier | Classification | Tolerance Criteria | Authority Required |
|---|---|---|---|
| **T1** | **Operational** | Budget $\le$ $100K, Cost Variance < 5%, Schedule Variance < 5 days, Contingency Spend < $10K | Project Manager (PM) |
| **T2** | **Controlled Change** | Cost Variance: 5%–10%, Schedule Variance: 5–15 days, Contingency Spend: $10K–$50K | PMO Director / Board |
| **T3** | **Governance Change** | Budget > $100K, Cost Variance > 10%, Schedule Variance > 15 days, Contingency Spend > $50K | **Project Sponsor (Executive)** |
| **T4** | **Enterprise Portfolio** | Cross-initiative budget shifts, resource contention, strategic alignment changes | **Executive Sponsor & Portfolio Board** |

> [!WARNING]
> **T3 & T4 Escapes**: When a project is classified as T3 or T4, the Governor Agent blocks automatic pipeline execution and appends a `[Governor Alert]` to the state, requiring a formal human validation sign-off.
