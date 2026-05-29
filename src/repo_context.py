"""Clones the sandbox repo and builds a code-context string for the LLM."""

import shutil
from pathlib import Path
from git import Repo


# File extensions we care about for the kanban project
ALLOWED_EXTENSIONS = {".js", ".html", ".css", ".json", ".md"}

# Folders/files to skip (build artifacts, dependencies, etc.)
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".vscode"}
SKIP_FILES = {"package-lock.json", ".DS_Store"}

# Safety cap — don't dump huge files into the prompt
MAX_FILE_BYTES = 50_000


class RepoContext:
    """Wraps a local clone of the sandbox repo + utilities to read it."""

    def __init__(self, repo_slug: str, work_dir: Path):
        self.repo_slug = repo_slug
        self.local_path = work_dir / repo_slug.split("/")[-1]
        self.repo: Repo | None = None

    def clone_or_refresh(self) -> Path:
        """Clone the repo fresh. Wipes any previous clone."""
        if self.local_path.exists():
            shutil.rmtree(self.local_path, ignore_errors=True)

        url = f"https://github.com/{self.repo_slug}.git"
        print(f"Cloning {url} → {self.local_path}")
        self.repo = Repo.clone_from(url, self.local_path)
        return self.local_path

    def list_source_files(self) -> list[Path]:
        """Return all relevant source files, filtered by extension and skip rules."""
        # print(f"DEBUG local_path: {self.local_path}")
        # print(f"DEBUG exists: {self.local_path.exists()}")
        # print(f"DEBUG contents: {list(self.local_path.iterdir()) if self.local_path.exists() else 'N/A'}")
        files = []
        # print(f"Walking: {self.local_path}")
        for path in self.local_path.rglob("*"):
            # print(f"  seen: {path}")
            if not path.is_file():
                continue
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue
            if path.name in SKIP_FILES:
                continue
            if path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            files.append(path)
        return sorted(files)

    def build_context_string(self) -> str:
        """Pack all source files into a single labeled string for the LLM."""
        parts = []
        for file_path in self.list_source_files():
            rel = file_path.relative_to(self.local_path)
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            if len(content.encode("utf-8")) > MAX_FILE_BYTES:
                content = content[:MAX_FILE_BYTES] + "\n... [truncated]"

            parts.append(f"--- FILE: {rel.as_posix()} ---\n{content}")

        return "\n\n".join(parts)


# if __name__ == "__main__":
#     config.validate()
#     ctx = RepoContext(config.SANDBOX_REPO, config.WORK_DIR)
#     ctx.clone_or_refresh()

#     files = ctx.list_source_files()
#     print(f"\nFound {len(files)} source files:")
#     for f in files:
#         print(f"  {f.relative_to(ctx.local_path)}")

#     context_str = ctx.build_context_string()
#     print(f"\n--- Context size: {len(context_str)} chars ---")
#     print(context_str[:500] + "...\n[truncated for preview]")
