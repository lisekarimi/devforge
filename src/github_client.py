"""GitHub App client: branch + commit + push + draft PR."""

import time
from pathlib import Path
import jwt
import requests
from git import Repo, Actor
import config


class GitHubAppClient:
    """Authenticates as a GitHub App installation and performs git/PR operations."""

    def __init__(self):
        self.app_id = config.GITHUB_APP_ID
        self.installation_id = config.GITHUB_APP_INSTALLATION_ID
        self.private_key_path = Path(config.GITHUB_APP_PRIVATE_KEY_PATH)
        self.repo_slug = config.SANDBOX_REPO  # e.g. "lisekarimi/365-POC-KANBAN"

        if not self.app_id or not self.installation_id:
            raise RuntimeError(
                "GITHUB_APP_ID and GITHUB_APP_INSTALLATION_ID must be set in .env"
            )
        if not self.private_key_path.exists():
            raise RuntimeError(f"Private key not found: {self.private_key_path}")

        self._installation_token: str | None = None
        self._token_expires_at: float = 0

    # ---------- Auth ----------

    def _generate_jwt(self) -> str:
        """Create a short-lived JWT signed with the app's private key."""
        now = int(time.time())
        payload = {
            "iat": now - 60,  # issued at (60s back to avoid clock skew)
            "exp": now + 9 * 60,  # expires in 9 minutes (max is 10)
            "iss": self.app_id,  # issuer = app id
        }
        private_key = self.private_key_path.read_text()
        return jwt.encode(payload, private_key, algorithm="RS256")

    def _get_installation_token(self) -> str:
        """Exchange the app JWT for a short-lived installation access token."""
        # Cache & reuse if still valid (tokens last ~1 hour)
        if self._installation_token and time.time() < self._token_expires_at - 60:
            return self._installation_token

        app_jwt = self._generate_jwt()
        url = f"https://api.github.com/app/installations/{self.installation_id}/access_tokens"
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._installation_token = data["token"]
        # GitHub returns ISO timestamp; rough expiry tracking
        self._token_expires_at = time.time() + 50 * 60
        return self._installation_token

    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_installation_token()}",
            "Accept": "application/vnd.github+json",
        }

    def _authed_clone_url(self) -> str:
        """A clone URL with the installation token embedded for git push."""
        token = self._get_installation_token()
        return f"https://x-access-token:{token}@github.com/{self.repo_slug}.git"

    # ---------- Git operations ----------

    def push_branch_with_changes(
        self,
        local_repo_path: Path,
        branch_name: str,
        commit_message: str,
    ) -> str:
        """Configure remote with token, create branch, commit changes, push.

        Returns the branch name.
        """
        repo = Repo(local_repo_path)

        # Update the remote to use the authenticated URL (for push)
        origin = repo.remote("origin")
        origin.set_url(self._authed_clone_url())

        # Create and checkout new branch from current HEAD
        if branch_name in [h.name for h in repo.heads]:
            repo.heads[branch_name].checkout()
        else:
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()

        # Stage all changes (the agent already wrote files to disk)
        repo.git.add(A=True)

        # If nothing to commit, skip cleanly
        if not repo.is_dirty(untracked_files=True):
            raise RuntimeError("No changes to commit — agent produced no diff.")

        author = Actor("365-PDLC-Agent", "agent@example.com")
        repo.index.commit(commit_message, author=author, committer=author)

        # Push
        print(f"🚀 Pushing branch {branch_name} to {self.repo_slug}...")
        origin.push(refspec=f"{branch_name}:{branch_name}", force=True)

        return branch_name

    # ---------- PR operations ----------

    def open_draft_pr(
        self,
        branch_name: str,
        title: str,
        body: str,
        base_branch: str = "main",
    ) -> dict:
        """Open a draft PR from branch_name → base_branch."""
        url = f"https://api.github.com/repos/{self.repo_slug}/pulls"
        payload = {
            "title": title,
            "head": branch_name,
            "base": base_branch,
            "body": body,
            "draft": True,
        }
        resp = requests.post(
            url, headers=self._auth_headers(), json=payload, timeout=30
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"PR creation failed: {resp.status_code} — {resp.text}")
        return resp.json()


def build_pr_body(ticket, agent_result) -> str:
    """Compose a PR description from the ticket + agent run results."""
    reasoning = "\n".join(f"- {r}" for r in agent_result.reasoning_log)
    validation_lines = []
    for r in agent_result.final_validation:
        emoji = "✅" if r.passed else "❌"
        validation_lines.append(f"{emoji} {r.name}")

    return f"""## 🎫 Ticket: {ticket.key}

**Summary:** {ticket.summary}

**Description:**
{ticket.description}

**Acceptance criteria:**
{chr(10).join(f"- {c}" for c in ticket.acceptance_criteria)}

---

## 🤖 Agent run

- **Attempts:** {agent_result.attempts}
- **Outcome:** {"✅ All validation passed" if agent_result.success else "❌ Validation failed"}

### Reasoning per attempt
{reasoning}

### Final validation
{chr(10).join(validation_lines)}

---

_Generated by 365-PDLC-Agent. Review carefully before merging._
"""


if __name__ == "__main__":
    config.validate()
    client = GitHubAppClient()
    # Smoke test: just fetch a token to confirm auth works
    token = client._get_installation_token()
    print(f"✅ Got installation token: {token[:20]}... (truncated)")
    print("GitHub App auth works.")
