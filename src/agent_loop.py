"""The retry loop: generate, validate, regenerate on failure, up to N attempts."""

from dataclasses import dataclass, field
from pathlib import Path
from src.code_generator import CodeGenerator
from src.policy_checker import PolicyChecker, PolicyViolation
from src.repo_context import RepoContext
from src.ticket_reader import Ticket
from src.validator import Validator, format_results, ValidationResult


@dataclass
class AgentRunResult:
    """Final outcome of an agent run."""

    success: bool
    attempts: int
    final_validation: list[ValidationResult] = field(default_factory=list)
    reasoning_log: list[str] = field(default_factory=list)
    last_changes: dict | None = None
    blocked: bool = False  # True if policy violated or LLM refused
    block_reason: str = ""  # human-readable explanation
    violations: list[PolicyViolation] = field(default_factory=list)


class AgentLoop:
    """Orchestrates generate → validate → retry until pass or max attempts."""

    def __init__(
        self,
        ticket: Ticket,
        repo_ctx: RepoContext,
        generator: CodeGenerator | None = None,
        max_attempts: int = 3,
        rules_path: Path | None = None,
    ):
        self.ticket = ticket
        self.repo_ctx = repo_ctx
        self.generator = generator or CodeGenerator()
        self.max_attempts = max_attempts

        # Load policies (default location: project_root/policies/rules.yaml)
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "policies" / "rules.yaml"
        self.policy_checker = PolicyChecker(rules_path)
        self.policy_text = self.policy_checker.rules_summary_for_prompt()

    def run(self) -> AgentRunResult:
        reasoning_log = []
        last_changes = None
        last_results: list[ValidationResult] = []

        for attempt in range(1, self.max_attempts + 1):
            print(f"\n{'=' * 60}")
            print(f"🤖 Attempt {attempt}/{self.max_attempts}")
            print(f"{'=' * 60}")

            self.repo_ctx.clone_or_refresh()
            print("📦 Building context...")
            repo_context_str = self.repo_ctx.build_context_string()
            print(f"📦 Context: {len(repo_context_str)} chars")

            print("🧠 Calling LLM (this takes 10-30s)...")
            if attempt == 1:
                changes = self.generator.generate(
                    self.ticket, repo_context_str, policy_text=self.policy_text
                )
            else:
                validation_summary = format_results(last_results)
                print(
                    f"\n📝 Sending validation errors back to LLM:\n{validation_summary[:500]}..."
                )
                changes = self.generator.regenerate(
                    self.ticket,
                    repo_context_str,
                    validation_errors=validation_summary,
                    policy_text=self.policy_text,
                )

            # --- Refusal path ---
            if changes.get("refused"):
                reason = changes.get("reasoning", "(no reason given)")
                rule_id = changes.get("rule_id", "UNKNOWN")
                print(f"\n🛑 LLM refused: rule {rule_id} — {reason}")
                return AgentRunResult(
                    success=False,
                    attempts=attempt,
                    reasoning_log=[f"Refused by LLM (rule {rule_id}): {reason}"],
                    blocked=True,
                    block_reason=f"Policy violation ({rule_id}): {reason}",
                )

            reasoning = changes.get("reasoning", "(none)")
            reasoning_log.append(f"Attempt {attempt}: {reasoning}")
            print(f"\n💭 Reasoning: {reasoning}")
            print(f"📄 Files to change: {[f['path'] for f in changes['files']]}")

            # --- Deterministic policy gate (catches LLM mistakes) ---
            violations = self.policy_checker.check_changes(changes)
            if violations:
                print(
                    f"\n🛑 Deterministic policy gate caught {len(violations)} violation(s):"
                )
                for v in violations:
                    print(f"  {v.summary()}")
                return AgentRunResult(
                    success=False,
                    attempts=attempt,
                    reasoning_log=reasoning_log,
                    last_changes=changes,
                    blocked=True,
                    block_reason=f"Policy violation detected by deterministic gate: {violations[0].rule_id}",
                    violations=violations,
                )

            # --- Apply + validate ---
            CodeGenerator.apply_changes(self.repo_ctx.local_path, changes)
            last_changes = changes

            print("🧪 Running validator...")
            validator = Validator(self.repo_ctx.local_path)
            overall, results = validator.run_all()
            last_results = results
            print(f"\n--- Validation ---\n{format_results(results)}")

            if overall:
                print(f"\n✅ Success on attempt {attempt}!")
                return AgentRunResult(
                    success=True,
                    attempts=attempt,
                    final_validation=results,
                    reasoning_log=reasoning_log,
                    last_changes=last_changes,
                )

            print(f"\n⚠️  Attempt {attempt} failed validation, retrying...")

        print(f"\n❌ Gave up after {self.max_attempts} attempts.")
        return AgentRunResult(
            success=False,
            attempts=self.max_attempts,
            final_validation=last_results,
            reasoning_log=reasoning_log,
            last_changes=last_changes,
        )


if __name__ == "__main__":
    import config
    from src.ticket_reader import load_ticket

    config.validate()

    fixture_path = Path(__file__).parent.parent / "fixtures" / "ticket_1.json"
    ticket = load_ticket(fixture_path)
    print(f"🎫 Ticket: {ticket.key} — {ticket.summary}")

    repo_ctx = RepoContext(config.SANDBOX_REPO, config.WORK_DIR)

    loop = AgentLoop(ticket=ticket, repo_ctx=repo_ctx, max_attempts=3)
    result = loop.run()

    print(f"\n{'=' * 60}")
    print(
        f"FINAL: {'✅ SUCCESS' if result.success else '❌ FAILED'} after {result.attempts} attempts"
    )
    print(f"{'=' * 60}")
