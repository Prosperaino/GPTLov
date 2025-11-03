from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Runtime configuration for LovChat."""

    raw_data_dir: Path = Path(os.getenv("LOVCHAT_RAW_DATA_DIR", "data/raw"))
    workspace_dir: Path = Path(os.getenv("LOVCHAT_WORKSPACE_DIR", "data/workspace"))
    openai_model: str = os.getenv("LOVCHAT_OPENAI_MODEL", "gpt-4o-mini")
    top_k: int = int(os.getenv("LOVCHAT_TOP_K", "5"))

    def ensure_directories(self) -> None:
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
