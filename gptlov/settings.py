from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _getenv(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value
    return default


@dataclass
class Settings:
    """Runtime configuration for GPTLov."""

    raw_data_dir: Path = Path(_getenv("GPTLOV_RAW_DATA_DIR", "LOVCHAT_RAW_DATA_DIR") or "data/raw")
    workspace_dir: Path = Path(
        _getenv("GPTLOV_WORKSPACE_DIR", "LOVCHAT_WORKSPACE_DIR") or "data/workspace"
    )
    openai_model: str = _getenv("GPTLOV_OPENAI_MODEL", "LOVCHAT_OPENAI_MODEL") or "gpt-4o-mini"
    top_k: int = int(_getenv("GPTLOV_TOP_K", "LOVCHAT_TOP_K") or "5")
    archives: tuple[str, ...] = field(default_factory=tuple)

    def ensure_directories(self) -> None:
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def __post_init__(self) -> None:
        env_archives = _getenv("GPTLOV_ARCHIVES", "LOVCHAT_ARCHIVES")
        if env_archives:
            parts = [part.strip() for part in env_archives.split(",") if part.strip()]
            self.archives = tuple(parts)
        elif not self.archives:
            self.archives = (
                "gjeldende-lover.tar.bz2",
                "gjeldende-sentrale-forskrifter.tar.bz2",
            )


settings = Settings()
settings.ensure_directories()
