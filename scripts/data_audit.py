from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abstract_classifier.commands.audit import main as audit_main


def main() -> int:
    return audit_main()


if __name__ == "__main__":
    raise SystemExit(main())
