
```
┌──────────────────────────────────────────────────────────────────┐
│  COMPLETE AI ENGINEERING AGENT — Production Architecture          │
└──────────────────────────────────────────────────────────────────┘

Jira (label: ai-augmented)
   ↓
Jira Automation (smart values + JSON escaping)
   ↓
Power Automate (HTTP orchestrator with branching)
   ↓
ngrok (public tunnel)
   ↓
FastAPI service
   ↓
Agent Loop — generate → policy → validate → retry
   ↓
GitHub App → branch + draft PR
   ↓
Power Automate → Jira comment + status transition (Review or Blocked)
   ↓
Human reviewer
```

## Features delivered

| Capability | Status |
|------------|--------|
| Read Jira ticket | ✅ |
| Read full codebase context | ✅ |
| Generate code + tests | ✅ |
| Self-correction retry loop | ✅ |
| Test validation gate | ✅ |
| Policy/compliance gate (YAML rules) | ✅ |
| LLM refusal on policy violation | ✅ |
| Deterministic policy double-check | ✅ |
| GitHub App authentication | ✅ |
| Draft PR with reasoning + validation summary | ✅ |
| Swappable LLM provider (OpenAI / Cerebras / Azure-ready) | ✅ |
| HTTP API for external orchestration | ✅ |
| Jira automation → Power Automate → Agent flow | ✅ |
| Comment-back on Jira with PR link | ✅ |
| Status transition: Review (success) | ✅ |
| Status transition: Blocked (policy violation) | ✅ |

## Architecture highlights

- **Clean separation**: code generator (developer), validator (QA), policy gate (security), GitHub client (VCS), loop (PM), API (service boundary)
- **Production-shaped**: clear interface for swapping any layer (model, orchestrator, repo host, ticketing system)
- **Compliance-ready foundation**: swap LLM to Azure AI Foundry with a single config change
- **Real Human-in-the-Loop**: draft PR + Jira comment, human always decides merge
- **Safe by default**: policy gate blocks risky tickets before code is written; deterministic Python check catches LLM mistakes

## What stakeholders will see in this demo

1. Create a Jira ticket → label it
2. ~30 seconds later: PR appears on GitHub + Jira comment + status in Review
3. Then create a **malicious ticket** (hardcoded API key)
4. Agent refuses, status moves to **Blocked**, no PR created, full audit trail

That two-scenario demo is **exactly** what enterprises want to see for trust + governance.

## Next steps when you're ready

These are optional polish/production items, not blockers:

1. **Move LLM to Azure AI Foundry** — one config change
2. **Deploy agent to Azure Container Apps** — ditch ngrok, get a stable URL
3. **Dedicated bot Jira account** — so comments don't show your name
4. **Audit logging to Log Analytics** — every prompt, completion, decision
5. **Sandbox execution** — run code in ephemeral containers, not on the agent host
6. **More tickets, more rules** — expand the test suite of scenarios
7. **README + diagrams** — polish for portfolio / pitch deck
