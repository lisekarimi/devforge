"""Deterministic policy gate. Scans agent-generated files for rule violations."""

import re
from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class PolicyViolation:
    """One violation found in one file."""

    rule_id: str
    description: str
    file_path: str
    matched_text: str | None = None

    def summary(self) -> str:
        loc = f" in `{self.file_path}`" if self.file_path else ""
        match = f" (matched: `{self.matched_text}`)" if self.matched_text else ""
        return f"❌ {self.rule_id}{loc}{match}"


class PolicyChecker:
    """Loads rules.yaml and checks proposed file changes against them."""

    def __init__(self, rules_path: Path):
        if not rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        self.rules_path = rules_path
        with open(rules_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.rules = self.config.get("rules", [])

    def check_changes(self, changes: dict) -> list[PolicyViolation]:
        """Scan every file change. Return list of violations (empty = all clean)."""
        violations: list[PolicyViolation] = []
        for file_change in changes.get("files", []):
            path = file_change["path"]
            content = file_change["content"]
            violations.extend(self._check_file(path, content))
        return violations

    def _check_file(self, path: str, content: str) -> list[PolicyViolation]:
        results: list[PolicyViolation] = []
        for rule in self.rules:
            rule_id = rule["id"]
            description = rule["description"]

            # Check forbidden file paths
            for forbidden_path in rule.get("forbidden_paths", []):
                if forbidden_path in path:
                    results.append(
                        PolicyViolation(rule_id, description, path, forbidden_path)
                    )

            # Check forbidden content patterns
            for pattern in rule.get("forbidden_patterns", []):
                m = re.search(pattern, content, re.IGNORECASE)
                if m:
                    results.append(
                        PolicyViolation(rule_id, description, path, m.group(0)[:80])
                    )
        return results

    def rules_summary_for_prompt(self) -> str:
        """Format rules as a readable block to inject into the LLM prompt."""
        lines = [
            "The following company engineering policies apply. You MUST refuse to make changes that violate any of them.\n"
        ]
        for rule in self.rules:
            lines.append(f"- **{rule['id']}**: {rule['description'].strip()}")
        return "\n".join(lines)


if __name__ == "__main__":
    rules_file = Path(__file__).parent.parent / "policies" / "rules.yaml"
    checker = PolicyChecker(rules_file)

    print(f"Loaded {len(checker.rules)} rules:")
    for rule in checker.rules:
        print(f"  - {rule['id']}")

    # Test scan: pretend the LLM tried to inject a secret
    fake_changes = {
        "files": [
            {
                "path": "app.js",
                "content": "const api_key = 'sk-abc123def456ghi789jkl012mno345pqr678'\nconsole.log('ok')",  # gitleaks:allow
            },
            {
                "path": ".env",
                "content": "SOMETHING=value",
            },
        ]
    }
    violations = checker.check_changes(fake_changes)
    print(f"\nFound {len(violations)} violations:")
    for v in violations:
        print(f"  {v.summary()}")
