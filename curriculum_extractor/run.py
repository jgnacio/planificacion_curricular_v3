"""
run.py — CLI entry point for the curriculum extractor.

Usage:
    python -m curriculum_extractor [options]
    python -m curriculum_extractor --dry-run
    python -m curriculum_extractor --tramos tramo_3 tramo_4
"""

import argparse
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv

import os

_repo_root = Path(__file__).parent.parent
load_dotenv(_repo_root / ".env")
load_dotenv(_repo_root / "teacher_agent" / ".env", override=True)

# Extractor runs locally via Gemini API (Google AI Studio), not Vertex AI
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"


def main():
    parser = argparse.ArgumentParser(
        description="Curriculum Extractor — Extracts ANEP/EBI curriculum data from PDFs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m curriculum_extractor
  python -m curriculum_extractor --dry-run
  python -m curriculum_extractor --tramos tramo_3 tramo_4
  python -m curriculum_extractor --config path/to/config.yaml
        """,
    )
    parser.add_argument(
        "--config",
        default="curriculum_extractor/config.yaml",
        help="Path to config.yaml (default: curriculum_extractor/config.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the result to stdout instead of writing to file.",
    )
    parser.add_argument(
        "--tramos",
        nargs="+",
        choices=["tramo_1", "tramo_2", "tramo_3", "tramo_4"],
        help="Process only specific tramos (default: all).",
    )
    args = parser.parse_args()

    # Validate config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        parser.error(f"Config file not found: {config_path}")

    # Import here to allow CLI to show help without requiring all deps
    from .merger import build_curriculum, write_output

    print(f"[run] Starting curriculum extraction")
    print(f"[run] Config: {config_path}")
    if args.tramos:
        print(f"[run] Tramos filter: {args.tramos}")
    if args.dry_run:
        print("[run] Dry run mode — output will be printed to stdout")

    result = build_curriculum(str(config_path), args.tramos)

    if args.dry_run:
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    else:
        # Load config to get output path
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        output_path = config.get("output_path", "data/curriculum_structure.json")

        # Resolve relative to repo root (parent of config's parent if config is inside package)
        config_dir = config_path.parent
        if config_dir.name == "curriculum_extractor":
            repo_root = config_dir.parent
        else:
            repo_root = Path(".")

        resolved_output = repo_root / output_path
        write_output(result, str(resolved_output))
        print(f"[run] Done. Written to {resolved_output}")


if __name__ == "__main__":
    main()
