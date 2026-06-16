from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .comparison import compare_analyses
from .config import load_config, validate_config
from .improvement import generate_improvements
from .ingest import ingest_unclassified_pdfs
from .lifecycle import load_status
from .local_retrieve import retrieve_local
from .pdf_chunk import chunk_common_category
from .pipeline import run_pipeline
from .plan_sync import sync_exec_plan
from .preflight import run_preflight, write_preflight_report
from .run_analyzer import analyze_results
from .runtime import ensure_runtime
from .runtime import create_run_id, doctor_summary, load_harness_env, make_worktree_id


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

    analyze = sub.add_parser("analyze", help="Normalize judge outputs and extract failure cases")
    analyze.add_argument("--result-dir", default="src/eval/infer_result")
    analyze.add_argument("--output-dir", default="")

    improve = sub.add_parser("improve", help="Create validated improvement candidates from an analysis")
    improve.add_argument("--analysis-dir", required=True)
    improve.add_argument("--output-dir", default="")
    improve.add_argument("--review-queue", default=".runtime/review_queue/improvement_queue.jsonl")

    compare = sub.add_parser("compare", help="Compare two analysis summaries")
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--output-dir", default="")

    plan_sync = sub.add_parser("plan-sync", help="Sync a markdown exec-plan into runtime lifecycle state")
    plan_sync.add_argument("--plan", default="docs/exec-plans/tech-debt-tracker.md")
    plan_sync.add_argument("-c", "--config", default="configs/harness.sample.json")
    plan_sync.add_argument("--worktree-id", default="")
    plan_sync.add_argument("--runtime-root", default="")

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

    if args.command == "analyze":
        output_dir = Path(args.output_dir) if args.output_dir else Path(".runtime") / "growth" / create_run_id()
        result = analyze_results(Path(args.result_dir), output_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "improve":
        output_dir = Path(args.output_dir) if args.output_dir else Path(args.analysis_dir) / "improvements"
        result = generate_improvements(Path(args.analysis_dir), output_dir, Path(args.review_queue))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "compare":
        output_dir = Path(args.output_dir) if args.output_dir else Path(".runtime") / "comparisons" / create_run_id()
        result = compare_analyses(Path(args.baseline), Path(args.candidate), output_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "plan-sync":
        config = load_config(args.config) if args.config else None
        runtime_root = Path(args.runtime_root) if args.runtime_root else config.runtime_root
        worktree_id = args.worktree_id or config.worktree_id
        result = sync_exec_plan(Path(args.plan), runtime_root, worktree_id)
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
