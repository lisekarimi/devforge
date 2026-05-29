"""Centralized config loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "gpt-oss-120b")

# GitHub App
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_APP_PRIVATE_KEY_PATH = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
GITHUB_APP_INSTALLATION_ID = os.getenv("GITHUB_APP_INSTALLATION_ID")
SANDBOX_REPO = os.getenv("SANDBOX_REPO")

# Paths
PROJECT_ROOT = Path(__file__).parent
WORK_DIR = PROJECT_ROOT / "tmp"
WORK_DIR.mkdir(exist_ok=True)


def validate():
    required = {
        "SANDBOX_REPO": SANDBOX_REPO,
    }
    if LLM_PROVIDER == "cerebras":
        required["CEREBRAS_API_KEY"] = CEREBRAS_API_KEY

    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}")
