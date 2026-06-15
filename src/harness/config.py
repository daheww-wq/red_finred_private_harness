from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .models import RedTeamCase


@dataclass(frozen=True)
class ProviderConfig:
    type: str
    model: str


@dataclass(frozen=True)
class HarnessConfig:
    run_name: str
    worktree_id: str
    runtime_root: Path
    generator: ProviderConfig
    reviewer: ProviderConfig
    allow_same_provider_for_roles: bool
    live_api_enabled: bool
    max_cases: int
    seed_cases: List[RedTeamCase]


def load_config(path: str | Path) -> HarnessConfig:
    cfg_path = Path(path)
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    return parse_config(raw, base_dir=cfg_path.parent)


def parse_config(raw: Dict[str, Any], base_dir: Path | None = None) -> HarnessConfig:
    providers = raw.get("providers", {})
    generator = _provider_config(providers.get("generator", {}), "generator")
    reviewer = _provider_config(providers.get("reviewer", {}), "reviewer")

    seed_cases = [RedTeamCase.from_dict(item) for item in raw.get("seed_cases", [])]
    runtime_root = Path(str(raw.get("runtime_root", ".runtime")))
    if base_dir and not runtime_root.is_absolute():
        runtime_root = (base_dir.parent / runtime_root).resolve()

    return HarnessConfig(
        run_name=str(raw.get("run_name", "harness-run")).strip(),
        worktree_id=str(raw.get("worktree_id", "local-worktree")).strip(),
        runtime_root=runtime_root,
        generator=generator,
        reviewer=reviewer,
        allow_same_provider_for_roles=bool(raw.get("allow_same_provider_for_roles", False)),
        live_api_enabled=bool(raw.get("live_api_enabled", False)),
        max_cases=int(raw.get("max_cases", len(seed_cases))),
        seed_cases=seed_cases,
    )


def validate_config(config: HarnessConfig) -> List[str]:
    errors: List[str] = []
    if not config.run_name:
        errors.append("run_name is required")
    if not config.worktree_id:
        errors.append("worktree_id is required")
    if config.max_cases < 1:
        errors.append("max_cases must be positive")
    if not config.seed_cases:
        errors.append("seed_cases must not be empty")
    if (
        config.generator.type == config.reviewer.type
        and config.generator.model == config.reviewer.model
        and not config.allow_same_provider_for_roles
    ):
        errors.append("generator and reviewer use the same provider/model without explicit allowance")
    for case in config.seed_cases:
        for err in case.validate():
            errors.append(f"{case.case_id or '<missing case_id>'}: {err}")
    for provider in (config.generator, config.reviewer):
        if provider.type not in {"fake", "openai", "gemini"}:
            errors.append(f"unsupported provider type: {provider.type}")
    if not config.live_api_enabled:
        for provider in (config.generator, config.reviewer):
            if provider.type in {"openai", "gemini"}:
                errors.append("live provider configured while live_api_enabled=false")
    return errors


def _provider_config(raw: Dict[str, Any], role: str) -> ProviderConfig:
    return ProviderConfig(
        type=str(raw.get("type", "fake")).strip().lower(),
        model=str(raw.get("model", f"fake-{role}-v1")).strip(),
    )
