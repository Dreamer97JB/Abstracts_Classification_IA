"""CLI wrapper: merge prediction CSVs for Phase 9 cross-model agreement (9E)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abstract_classifier.pseudo_label_merge import merge_prediction_csvs_cli


def main() -> int:
    return merge_prediction_csvs_cli()


if __name__ == "__main__":
    raise SystemExit(main())
