from __future__ import annotations

from pathlib import Path
from typing import Iterable


def assert_no_existing_outputs(paths: Iterable[Path], overwrite: bool = False) -> None:
    if overwrite:
        return
    existing = [path for path in paths if _has_output(path)]
    if existing:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"output already exists; pass --overwrite to replace: {joined}")


def _has_output(path: Path) -> bool:
    if path.is_file():
        return True
    if path.is_dir():
        return any(path.iterdir())
    return False
