from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .methodology_pipeline import (
    DEFAULT_METHODOLOGY_BASELINE_CONFIG,
    load_analysis_input_rows,
    load_methodology_baseline_config,
    load_reviewed_methodology_labels,
    build_methodology_assignments,
    write_methodology_outputs,
)
from .taxonomy import ROOT
from .theme_analysis import (
    DEFAULT_THEME_PIPELINE_CONFIG,
    build_theme_outputs,
    load_theme_pipeline_config,
)
from .text_variants import load_governed_text_metadata


@dataclass(frozen=True)
class AnalysisRunArtifacts:
    run_dir: Path
    manifest_path: Path
    methodology_artifacts: dict[str, Path]
    theme_artifacts: dict[str, Path]


def run_analysis_bundle(
    *,
    run_id: str,
    input_artifact: str | Path,
    output_dir: str | Path | None = None,
    methodology_config_path: str | Path = DEFAULT_METHODOLOGY_BASELINE_CONFIG,
    theme_config_path: str | Path = DEFAULT_THEME_PIPELINE_CONFIG,
    reviewed_methodology_artifact: str | Path | None = None,
    text_variant: str | None = None,
    skip_methodology: bool = False,
    skip_themes: bool = False,
    root: Path | None = None,
) -> AnalysisRunArtifacts:
    project_root = root or ROOT
    methodology_config = load_methodology_baseline_config(
        methodology_config_path,
        root=project_root,
    )
    theme_config = load_theme_pipeline_config(theme_config_path, root=project_root)
    run_dir = _resolve_analysis_run_dir(
        output_dir=output_dir,
        default_output_root=methodology_config.default_output_root,
        run_id=run_id,
        root=project_root,
    )
    run_dir.mkdir(parents=True, exist_ok=True)

    input_rows = load_analysis_input_rows(input_artifact, root=project_root)
    text_metadata = load_governed_text_metadata(
        root=project_root,
        supervision_config_path=methodology_config.supervision_config_path,
    )

    methodology_artifacts: dict[str, Path] = {}
    theme_artifacts: dict[str, Path] = {}
    assignments = None

    if not skip_methodology:
        assignments = build_methodology_assignments(
            input_rows,
            config=methodology_config,
            text_variant=text_variant,
            text_metadata=text_metadata,
            root=project_root,
        )
        reviewed_labels = None
        if reviewed_methodology_artifact is not None:
            reviewed_labels = load_reviewed_methodology_labels(
                reviewed_methodology_artifact,
                root=project_root,
            )
        methodology_outputs = write_methodology_outputs(
            assignments,
            run_dir=run_dir,
            reviewed_labels=reviewed_labels,
            root=project_root,
        )
        methodology_artifacts = {
            "assignments": methodology_outputs.assignments_path,
            "review_queue": methodology_outputs.review_queue_path,
            "summary": methodology_outputs.summary_path,
            **methodology_outputs.metrics_paths,
        }

    if not skip_themes:
        theme_input_rows = assignments if assignments is not None else input_rows
        theme_assignments, theme_summary = build_theme_outputs(
            theme_input_rows,
            config=theme_config,
            text_metadata=text_metadata,
            root=project_root,
        )
        theme_assignments_path = run_dir / "theme_assignments.csv"
        theme_summary_path = run_dir / "theme_summary.csv"
        theme_assignments.to_csv(theme_assignments_path, index=False, encoding="utf-8")
        theme_summary.to_csv(theme_summary_path, index=False, encoding="utf-8")
        theme_artifacts = {
            "assignments": theme_assignments_path,
            "summary": theme_summary_path,
        }

    manifest = {
        "run_id": run_id,
        "input_artifact": _relative_path(Path(input_artifact), project_root),
        "output_directory": _relative_path(run_dir, project_root),
        "methodology": {
            "config_path": _relative_path(methodology_config.config_path, project_root),
            "text_variant": text_variant or methodology_config.default_text_variant,
            "artifacts": {
                key: _relative_path(path, project_root)
                for key, path in methodology_artifacts.items()
            },
        },
        "themes": {
            "config_path": _relative_path(theme_config.config_path, project_root),
            "artifacts": {
                key: _relative_path(path, project_root)
                for key, path in theme_artifacts.items()
            },
        },
        "skip_methodology": skip_methodology,
        "skip_themes": skip_themes,
        "reviewed_methodology_artifact": (
            _relative_path(Path(reviewed_methodology_artifact), project_root)
            if reviewed_methodology_artifact is not None
            else ""
        ),
    }
    manifest_path = run_dir / "analysis_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return AnalysisRunArtifacts(
        run_dir=run_dir,
        manifest_path=manifest_path,
        methodology_artifacts=methodology_artifacts,
        theme_artifacts=theme_artifacts,
    )


def _resolve_analysis_run_dir(
    *,
    output_dir: str | Path | None,
    default_output_root: Path,
    run_id: str,
    root: Path,
) -> Path:
    if output_dir is not None:
        candidate = Path(output_dir)
        if not candidate.is_absolute():
            candidate = root / candidate
        return candidate.resolve()
    return (default_output_root / run_id).resolve()


def _relative_path(path: Path, root: Path) -> str:
    candidate = path
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(candidate.resolve())
