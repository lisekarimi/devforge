"""Loads and validates a fake Jira ticket from a JSON file."""

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class Ticket(BaseModel):
    """A minimal Jira-like ticket. Mirrors what we'd get from the Jira API later."""

    key: str
    summary: str
    description: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    target_files_hint: Optional[list[str]] = None

    def is_ai_augmented(self) -> bool:
        return "ai-augmented" in [label.lower() for label in self.labels]

    def to_prompt_section(self) -> str:
        """Format the ticket as a clean block for the LLM prompt."""
        criteria = "\n".join(f"  - {c}" for c in self.acceptance_criteria)
        hint = (
            f"\nLikely files to modify: {', '.join(self.target_files_hint)}"
            if self.target_files_hint
            else ""
        )
        return (
            f"TICKET {self.key}\n"
            f"Summary: {self.summary}\n\n"
            f"Description:\n{self.description}\n\n"
            f"Acceptance criteria:\n{criteria}"
            f"{hint}"
        )


def load_ticket(path: str | Path) -> Ticket:
    """Load a ticket JSON file into a validated Ticket model."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Ticket file not found: {path}")
    data = json.loads(path.read_text())
    return Ticket(**data)


if __name__ == "__main__":
    ticket = load_ticket("fixtures/ticket_1.json")
    print(f"Loaded: {ticket.key}")
    print(f"AI-augmented? {ticket.is_ai_augmented()}")
    print("\n--- Prompt section ---")
    print(ticket.to_prompt_section())
