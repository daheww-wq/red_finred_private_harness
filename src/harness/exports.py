from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


def export_accepted(
    sources: Iterable[Path],
    export_root: Path = Path("exports/accepted"),
    manifest_name: str = "manifest.json",
    overwrite: bool = False,
) -> Dict[str, Any]:
    export_root.mkdir(parents=True, exist_ok=True)
    copied: List[Dict[str, str]] = []
    for source in sources:
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(str(source))
        target = export_root / source.name
        if target.exists() and not overwrite:
            raise FileExistsError(f"accepted export already exists: {target}")
        shutil.copy2(source, target)
        copied.append({"source": str(source), "target": str(target)})

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "export_root": str(export_root),
        "files": copied,
    }
    (export_root / manifest_name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
