# 🛠️ DevForge

An AI-powered software engineering agent that picks up Jira tickets, writes code, runs tests, and opens draft pull requests — with a built-in policy gate that refuses tickets which would violate company engineering rules.

## What it does

When a Jira ticket is labeled `ai-augmented`, the agent:

1. Reads the ticket (summary, description, acceptance criteria)
2. Clones the target repository and reads the full codebase
3. Checks the request against company policies (loaded from `policies/rules.yaml`)
4. If the ticket would violate a policy → **refuses**, posts a Blocked comment on Jira, and transitions the ticket to **Blocked**. No code is written.
5. Otherwise, generates source code **and tests**
6. Runs syntax checks and the project's test suite
7. Self-corrects on validation failure (up to 3 retry attempts), feeding errors back to the LLM
8. Pushes a new branch and opens a **draft pull request** on GitHub
9. Comments on the Jira ticket with the PR link, agent reasoning, and validation summary
10. Transitions the Jira ticket to **Review** for a human to approve

A human reviews every PR before merge — the agent never merges code on its own.

## Architecture

The agent runs as an HTTP service. Two orchestration layers sit in front:

- **Jira Automation** detects the `ai-augmented` label and sends the ticket payload to Power Automate
- **Power Automate** calls the agent, then branches on the response: success → Review, blocked → Blocked, with appropriate comments
- **Agent (Python)** does the engineering work: read, plan, generate, validate, retry, commit, PR

LLM access is swappable via environment variables (currently OpenAI and Cerebras supported; Azure AI Foundry is a drop-in for enterprise use).

GitHub access uses a **GitHub App** with fine-grained permissions scoped to a single repository — no personal access tokens.

## Tech stack

- Python 3.11 with `uv` for dependency management
- FastAPI + Uvicorn for the HTTP service
- OpenAI Python SDK (Cerebras compatible — same SDK, different `base_url`)
- PyGithub + GitPython for repository operations
- PyJWT + cryptography for GitHub App authentication
- PyYAML for policy rules
- ngrok for local development tunneling
- Jira Automation + Power Automate for orchestration

## Prerequisites

Before running, you need:

- **Python 3.11+** and [uv](https://docs.astral.sh/uv/) installed
- **Node.js 20+** (the agent's validator runs `node --check` and `node --test` against the sandbox repo)
- **An LLM provider API key** — OpenAI or Cerebras (recommended for cost + speed)
- **A GitHub App** installed on the target sandbox repository, with permissions:
  - Contents: Read & write
  - Pull requests: Read & write
  - Metadata: Read
- The GitHub App's **private key (`.pem`)** saved locally
- **ngrok** account + authtoken (for exposing the local agent to Jira/Power Automate)
- **A Jira Cloud project** with the `ai-augmented` label and an automation rule pointing at the Power Automate URL
- **A Power Automate flow** with an HTTP trigger that calls the agent and branches on the response

## Configuration

Create a `.env` file at the project root:

```env
# LLM provider
LLM_PROVIDER=cerebras           # or "openai"
CEREBRAS_API_KEY=csk-...
CEREBRAS_MODEL=gpt-oss-120b
OPENAI_API_KEY=sk-...           # only required if LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini

# Target sandbox repository
SANDBOX_REPO=owner/repo-name

# GitHub App
GITHUB_APP_ID=1234567
GITHUB_APP_PRIVATE_KEY_PATH=./github-app-key.pem
GITHUB_APP_INSTALLATION_ID=12345678
```

Policy rules live in `policies/rules.yaml` and are loaded at runtime. Edit this file to add, remove, or modify engineering constraints — no code change required.

## How to launch

Install dependencies:

```bash
uv sync
```

Start the HTTP service:

```bash
uv run uvicorn api:app --reload --port 8000
```

In a second terminal, expose the service publicly:

```bash
ngrok http 8000
```

Copy the `https://*.ngrok-free.app` URL and paste it into the **Send web request** action of your Jira automation rule (or the HTTP action in your Power Automate flow, depending on your orchestration setup).

The agent is now live. Add the `ai-augmented` label to any Jira ticket in the configured project, and within ~30 seconds you should see a comment on the ticket with a PR link (or a Blocked notification if the ticket violates a policy).

## Running the agent without Jira

For local testing, use the CLI:

```bash
uv run python agent.py --ticket fixtures/ticket_1.json
```

Or hit the HTTP endpoint directly:

```bash
curl -X POST http://localhost:8000/process-ticket \
  -H "Content-Type: application/json" \
  -d @fixtures/ticket_1.json
```

## Project layout

```
365-pdlc-agent/
├── api.py                      # FastAPI HTTP service
├── agent.py                    # CLI entry point
├── config.py                   # Env loading + validation
├── policies/
│   └── rules.yaml              # Engineering policies the agent enforces
├── fixtures/                   # Sample ticket payloads for testing
├── src/
│   ├── llm_client.py           # Swappable LLM wrapper
│   ├── ticket_reader.py        # Loads + validates ticket JSON
│   ├── repo_context.py         # Clones the sandbox repo, builds prompt context
│   ├── code_generator.py       # Prompts the LLM, parses file changes / refusals
│   ├── policy_checker.py       # Deterministic policy gate
│   ├── validator.py            # Runs syntax checks + tests
│   ├── agent_loop.py           # Orchestrates generate → policy → validate → retry
│   └── github_client.py        # GitHub App auth, branch + draft PR
└── tmp/                        # Working clones (gitignored, wiped per run)
```

## Notes

- The agent is intentionally narrow in scope: it picks up tickets, makes code changes in a sandbox repo, and opens draft PRs. It does not merge, deploy, or modify production configuration.
- All LLM traffic can be routed through Azure AI Foundry by changing two lines in `src/llm_client.py` — the project is built to be compliance-ready.
- The retry loop uses validator failures as feedback to the LLM. This is the key behavior that makes the agent "agentic" rather than a one-shot generator.
- Policies are enforced in two layers: the LLM is asked to refuse policy-violating tickets in its prompt, AND a deterministic Python check scans every generated file against pattern rules. Both must pass.
