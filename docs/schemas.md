Almost — but you've got **nested fences** which break Markdown rendering on GitHub. You have ` ```` ` (4 backticks) wrapping ` ``` ` (3 backticks). Most renderers see this as broken.

## Clean version — use this in your README

## Schema 1 — Technical Architecture

```mermaid
---
title: Technical Architecture
---
flowchart TB
    subgraph External["🌐 External Systems"]
        Jira[Jira Cloud<br/>Ticket + label]
        GitHub[GitHub<br/>Sandbox repo + draft PR]
        LLM[LLM Provider<br/>Cerebras / Azure AI Foundry]
    end

    subgraph Orchestration["⚙️ Orchestration Layer"]
        JiraAuto[Jira Automation<br/>Trigger on label]
        PowerAuto[Power Automate<br/>Branching + Comments + Status]
    end

    subgraph Agent["🤖 Agent Service · FastAPI"]
        direction TB
        Loop{{Agent Loop<br/>up to 3 attempts}}
        Gen[Code Generator<br/>LLM prompt + parse]
        Policy[Policy Gate<br/>LLM refusal + Python scan]
        Val[Validator<br/>Syntax + Tests]
        GH[GitHub Client<br/>Branch + Draft PR]

        Loop --> Gen
        Gen --> Policy
        Policy -->|Pass| Val
        Val -->|Fail| Loop
        Val -->|Pass| GH
        Policy -.->|Block| Loop
    end

    Jira -->|Label added| JiraAuto
    JiraAuto -->|HTTP POST| PowerAuto
    PowerAuto -->|HTTP POST| Loop
    Gen <-->|Prompt + Response| LLM
    GH -->|Push + PR| GitHub
    Loop -->|Outcome| PowerAuto
    PowerAuto -->|Comment + Transition| Jira

    classDef external fill:#3B82F6,stroke:#1D4ED8,color:#fff,stroke-width:2px
    classDef orch fill:#F59E0B,stroke:#B45309,color:#fff,stroke-width:2px
    classDef agent fill:#10B981,stroke:#047857,color:#fff,stroke-width:2px

    class Jira,GitHub,LLM external
    class JiraAuto,PowerAuto orch
    class Loop,Gen,Policy,Val,GH agent
```

## Schema 2 — User Journey

```mermaid
---
title: User Journey — From Ticket to Reviewed Code
---
flowchart LR
    Dev([Developer]) -->|Creates ticket<br/>adds 'ai-augmented' label| T1[Ticket created<br/>in Jira]

    T1 -->|~30 seconds<br/>automated| Check{Policy<br/>check passes?}

    Check -->|Yes| Gen[Agent generates<br/>code + tests]
    Gen --> ValCheck{Tests<br/>pass?}
    ValCheck -->|Yes| PR[Draft PR opened<br/>+ Jira comment<br/>+ status: Review]
    ValCheck -->|No, 3 attempts| Failed[Status: Failed<br/>+ Jira comment]

    Check -->|No| Blocked[No code written<br/>Status: Blocked<br/>+ rule explanation]

    PR --> Reviewer([Reviewer])
    Blocked --> Reviewer
    Failed --> Reviewer

    Reviewer -->|Reviews PR| Decision{Approve?}
    Decision -->|Yes| Merge[Merge to main]
    Decision -->|Request changes| Dev

    classDef person fill:#8B5CF6,stroke:#6D28D9,color:#fff,stroke-width:2px
    classDef happy fill:#10B981,stroke:#047857,color:#fff,stroke-width:2px
    classDef sad fill:#EF4444,stroke:#B91C1C,color:#fff,stroke-width:2px
    classDef step fill:#3B82F6,stroke:#1D4ED8,color:#fff,stroke-width:2px

    class Dev,Reviewer person
    class PR,Merge happy
    class Blocked,Failed sad
    class T1,Gen,Check,ValCheck,Decision step
```
