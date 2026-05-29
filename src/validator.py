"""Runs validation (tests + syntax checks) on the modified clone."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    """Outcome of a single validation step."""

    name: str
    passed: bool
    stdout: str
    stderr: str
    returncode: int

    def summary(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} — {self.name}"


class Validator:
    """Runs a series of checks against the repo at `repo_root`."""

    def __init__(self, repo_root: Path, timeout_seconds: int = 60):
        self.repo_root = repo_root
        self.timeout = timeout_seconds

    def _run(self, name: str, cmd: list[str]) -> ValidationResult:
        """Execute a shell command in the repo root and capture output."""
        print(f"▶️  Running: {name}  →  {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return ValidationResult(
                name=name,
                passed=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                name=name,
                passed=False,
                stdout="",
                stderr=f"Timed out after {self.timeout}s",
                returncode=-1,
            )
        except FileNotFoundError as e:
            return ValidationResult(
                name=name,
                passed=False,
                stdout="",
                stderr=f"Command not found: {e}",
                returncode=-1,
            )

    def syntax_check_js(self) -> ValidationResult:
        """Quick syntax check on app.js using `node --check`."""
        return self._run("JS syntax check", ["node", "--check", "app.js"])

    def run_tests(self) -> ValidationResult:
        """Run the project's tests using node's built-in test runner."""
        tests_dir = self.repo_root / "tests"
        if not tests_dir.exists():
            return ValidationResult(
                name="Tests",
                passed=True,
                stdout="(no tests directory)",
                stderr="",
                returncode=0,
            )
        # Collect all .js test files explicitly — Node 24 doesn't accept "tests/"
        test_files = sorted(
            str(p.relative_to(self.repo_root)) for p in tests_dir.rglob("*.js")
        )
        if not test_files:
            return ValidationResult(
                name="Tests",
                passed=True,
                stdout="(no test files found)",
                stderr="",
                returncode=0,
            )
        return self._run("Node tests", ["node", "--test", *test_files])

    def run_all(self) -> tuple[bool, list[ValidationResult]]:
        """Run every check. Returns (overall_pass, list_of_results)."""
        checks = [
            self.syntax_check_js(),
            self.run_tests(),
        ]
        overall = all(c.passed for c in checks)
        return overall, checks


def format_results(results: list[ValidationResult]) -> str:
    """Pretty-print all results, including stderr for failures."""
    lines = []
    for r in results:
        lines.append(r.summary())
        if not r.passed:
            if r.stdout.strip():
                lines.append(f"  stdout:\n{_indent(r.stdout)}")
            if r.stderr.strip():
                lines.append(f"  stderr:\n{_indent(r.stderr)}")
    return "\n".join(lines)


def _indent(text: str, prefix: str = "    ") -> str:
    return "\n".join(prefix + line for line in text.strip().splitlines())


if __name__ == "__main__":
    import config

    config.validate()
    repo_root = config.WORK_DIR / config.SANDBOX_REPO.split("/")[-1]

    if not repo_root.exists():
        raise SystemExit(
            f"Repo not found at {repo_root}. Run `python -m src.code_generator` first."
        )

    validator = Validator(repo_root)
    overall, results = validator.run_all()

    print("\n--- Validation results ---")
    print(format_results(results))
    print(f"\nOverall: {'✅ ALL CHECKS PASSED' if overall else '❌ VALIDATION FAILED'}")
