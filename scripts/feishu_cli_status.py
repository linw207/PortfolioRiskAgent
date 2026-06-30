from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.infra.external.feishu_client import FeishuCLIClient


def main() -> None:
    print(json.dumps(FeishuCLIClient().status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
