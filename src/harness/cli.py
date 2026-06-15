from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config, validate_config
from .ingest import ingest_unclassified_pdfs
from .lifecycle import load_status
from .local_retrieve import retrieve_local
from .pdf_chunk import chunk_common_category
from .pipeline import run_pipeline
from .preflight import run_preflight, write_preflight_report
from .runtime import ensure_runtime
from .runtime import doctor_summary, load_harness_env, make_worktree_id


def main(argv: list[str] | None = None) -> int:
    load_harness_env(Path.cwd())

    parser = argparse.ArgumentParser(description="Financial red-team harness CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Check local harness environment")

    validate = sub.add_parser("validate-config", help="Validate a harness config")
    validate.add_argument("-c", "--config", required=True)

    preflight = sub.add_parser("preflight", help="Inspect code, folders, and configuration before a run")
    preflight.add_argument("-c", "--config", required=True)

    run = sub.add_parser("run", help="Run the harness pipeline")
    run.add_argument("-c", "--config", required=True)

    resume = sub.add_parser("resume", help="Resume the harness pipeline")
    resume.add_argument("-c", "--config", required=True)

    status = sub.add_parser("status", help="Show lifecycle state for a config")
    status.add_argument("-c", "--config", required=True)

    worktree_doctor = sub.add_parser("worktree-doctor", help="Show computed worktree identity")
    worktree_doctor.add_argument("--repo-name", default=Path.cwd().name)
    worktree_doctor.add_argument("--branch-name", default="no-git")
    worktree_doctor.add_argument("--head", default="nohead")

    ingest = sub.add_parser("ingest-pdfs", help="Scan unclassified PDFs and draft R1-R5 routing records")
    ingest.add_argument("--move", action="store_true", help="Move routed PDFs from unclassified into R1-R5 folders")
    ingest.add_argument("--force", action="store_true", help="Replace existing routing records for scanned PDFs")

    chunk_pdfs = sub.add_parser("chunk-pdfs", help="Chunk routed common PDFs with a fast pypdf parser")
    chunk_pdfs.add_argument("--category", required=True, choices=["R1", "R2", "R3", "R4", "R5"])
    chunk_pdfs.add_argument("--overwrite", action="store_true")

    local_retrieve = sub.add_parser("local-retrieve", help="Retrieve chunks locally without embedding API calls")
    local_retrieve.add_argument("--category", required=True)
    local_retrieve.add_argument("--top-k", type=int, default=12)

    args = parser.parse_args(argv)

    if args.command == "doctor":
        print(json.dumps(doctor_summary(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "worktree-doctor":
        print(make_worktree_id(args.repo_name, args.branch_name, args.head))
        return 0

    if args.command == "ingest-pdfs":
        result = ingest_unclassified_pdfs(Path.cwd(), move_files=args.move, force=args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "chunk-pdfs":
        result = chunk_common_category(Path.cwd(), category=args.category, overwrite=args.overwrite)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not result["errors"] else 2

    if args.command == "local-retrieve":
        result = retrieve_local(Path.cwd(), category_prefix=args.category, top_k=args.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "validate-config":
        config = load_config(args.config)
        errors = validate_config(config)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
            return 2
        print(json.dumps({"valid": True}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "preflight":
        config = load_config(args.config)
        paths = ensure_runtime(config.runtime_root, config.worktree_id)
        report = run_preflight(config, Path.cwd())
        write_preflight_report(paths.state / "preflight.json", report)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 0 if report.passed else 2

    if args.command == "status":
        config = load_config(args.config)
        paths = ensure_runtime(config.runtime_root, config.worktree_id)
        print(json.dumps(load_status(paths.state), ensure_ascii=False, indent=2))
        return 0

    if args.command in {"run", "resume"}:
        config = load_config(args.config)
        errors = validate_config(config)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
            return 2
        report = run_pipeline(config, resume=args.command == "resume", config_path=args.config)
        print(json.dumps({"report": str(report)}, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
