from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.service.evaluation.official import OfficialBenchmarkService


def main() -> None:
    parser = argparse.ArgumentParser(description="Check optional official BFCL/GAIA benchmark integration.")
    parser.add_argument("--gaia-sample", action="store_true", help="Load a small GAIA sample from HuggingFace.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--level", type=int, default=None)
    parser.add_argument("--bfcl-mode", choices=["status", "generate", "evaluate"], default="status")
    parser.add_argument("--gaia-eval", action="store_true", help="Run GAIA agent answering and local exact-match scoring.")
    parser.add_argument("--gaia-config", default="2023_level1")
    parser.add_argument("--gaia-split", default="validation")
    parser.add_argument("--no-save", action="store_true", help="Do not save GAIA evaluation JSON/Markdown outputs.")
    args = parser.parse_args()

    service = OfficialBenchmarkService()
    result = {
        "status": service.status(),
        "bfcl": service.run_bfcl_cli(args.bfcl_mode),
    }
    if args.gaia_sample:
        result["gaia_sample"] = service.load_gaia_sample(limit=args.limit, level=args.level)
    if args.gaia_eval:
        result["gaia_evaluation"] = service.run_gaia_evaluation(
            limit=args.limit,
            level=args.level,
            config=args.gaia_config,
            split=args.gaia_split,
            save=not args.no_save,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
