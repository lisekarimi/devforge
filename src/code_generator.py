"""Builds the prompt, calls the LLM, and parses the response into file changes."""

import json
import re
from pathlib import Path
from src.llm_client import LLMClient
from src.ticket_reader import Ticket


SYSTEM_PROMPT = """You are an AI software engineering agent.

You receive a ticket describing a change to make to a small codebase. You must:
1. Understand the ticket and acceptance criteria
2. Check whether the ticket would require violating any company policy
3. If policy would be violated → REFUSE and explain which rule
4. Otherwise → decide which files to change and return their full content

OUTPUT FORMAT — strict JSON, nothing else, no markdown fences:

If the ticket is OK:
{
  "reasoning": "Brief explanation of your approach (2-3 sentences)",
  "files": [
    {"path": "relative/path.ext", "content": "FULL new file content"}
  ]
}

If the ticket violates a policy:
{
  "refused": true,
  "rule_id": "ID_OF_THE_VIOLATED_RULE",
  "reasoning": "Plain-English explanation of why this ticket cannot be done"
}

RULES:
- Only include files you actually changed. Do not return unchanged files.
- Always return the COMPLETE file content, not a diff or snippet.
- Keep changes minimal and focused on the ticket.
- Preserve existing code style and conventions.
- Do not invent dependencies, frameworks, or files that don't exist.
- If tests exist, ensure your changes don't break them.
- When you add a new feature, also add or update tests that verify it works.
- When you fix a bug, add a regression test that would have caught it.
- Tests go in the `tests/` directory and follow the existing test framework (node --test).
"""


USER_TEMPLATE = """{ticket}

--- CURRENT CODEBASE ---
{repo_context}

--- END CODEBASE ---

Generate the file changes needed to satisfy this ticket. Respond with the JSON object only.
"""


RETRY_USER_TEMPLATE = """{ticket}

--- CURRENT CODEBASE ---
{repo_context}

--- END CODEBASE ---

--- PREVIOUS ATTEMPT FAILED ---
You already tried to solve this ticket. Your previous changes produced these validation failures:

{validation_errors}

Analyze the failures carefully and produce a corrected solution. Common pitfalls to avoid:
- Don't use jQuery-only selectors like `:contains()` with `document.querySelector`
- Make sure all code runs in both browser and Node test environments
- Verify that any DOM API you use actually exists in vanilla JS

Respond with the JSON object only.
"""


class CodeGenerator:
    """Asks the LLM to produce file changes for a ticket."""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def generate(
        self, ticket: Ticket, repo_context: str, policy_text: str = ""
    ) -> dict:
        """Return a dict with either file changes OR a refusal."""
        user_prompt = USER_TEMPLATE.format(
            ticket=ticket.to_prompt_section(),
            repo_context=repo_context,
        )
        if policy_text:
            user_prompt = f"--- COMPANY POLICIES ---\n{policy_text}\n\n{user_prompt}"

        raw = self.llm.generate(system=SYSTEM_PROMPT, user=user_prompt, temperature=0.2)
        return self._parse_response(raw)

    @staticmethod
    def _parse_response(raw: str) -> dict:
        """Strip any markdown fences and parse JSON."""
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"LLM did not return valid JSON.\nError: {e}\nRaw (first 500 chars):\n{raw[:500]}"
            )

        # A refusal is a valid response — no files needed
        if data.get("refused"):
            return data

        if "files" not in data or not isinstance(data["files"], list):
            raise ValueError(
                f"Response missing 'files' list. Got keys: {list(data.keys())}"
            )
        return data

    @staticmethod
    def apply_changes(repo_root: Path, changes: dict) -> list[Path]:
        """Write each file change to disk. Returns list of written paths."""
        written = []
        for file_change in changes["files"]:
            target = repo_root / file_change["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(file_change["content"], encoding="utf-8")
            written.append(target)
            print(f"  ✏️  wrote {file_change['path']}")
        return written

    def regenerate(
        self,
        ticket: Ticket,
        repo_context: str,
        validation_errors: str,
        policy_text: str = "",
    ) -> dict:
        user_prompt = RETRY_USER_TEMPLATE.format(
            ticket=ticket.to_prompt_section(),
            repo_context=repo_context,
            validation_errors=validation_errors,
        )
        if policy_text:
            user_prompt = f"--- COMPANY POLICIES ---\n{policy_text}\n\n{user_prompt}"
        raw = self.llm.generate(system=SYSTEM_PROMPT, user=user_prompt, temperature=0.2)
        return self._parse_response(raw)


if __name__ == "__main__":
    import config
    from src.ticket_reader import load_ticket
    from src.repo_context import RepoContext

    config.validate()

    # Load ticket
    fixture_path = Path(__file__).parent.parent / "fixtures" / "ticket_1.json"
    ticket = load_ticket(fixture_path)
    print(f"Ticket loaded: {ticket.key}\n")

    # Clone repo + build context
    ctx = RepoContext(config.SANDBOX_REPO, config.WORK_DIR)
    ctx.clone_or_refresh()
    repo_context = ctx.build_context_string()
    print(f"Context built: {len(repo_context)} chars\n")

    # Generate changes
    gen = CodeGenerator()
    print("Calling LLM...")
    changes = gen.generate(ticket, repo_context)

    print(f"\n--- Reasoning ---\n{changes.get('reasoning', '(none)')}\n")
    print(f"--- {len(changes['files'])} file(s) to change ---")
    for f in changes["files"]:
        print(f"  📄 {f['path']} ({len(f['content'])} chars)")

    # Apply changes locally
    print("\n--- Applying changes ---")
    CodeGenerator.apply_changes(ctx.local_path, changes)
    print("\n✅ Done. Check the files in tmp/365-POC-KANBAN to see what changed.")
