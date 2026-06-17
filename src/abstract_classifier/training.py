from __future__ import annotations

import json
import platform
import sys
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import Normalizer
from sklearn.pipeline import Pipeline

from .taxonomy import ROOT, load_taxonomy, resolve_project_path
from .text_variants import (
    build_text_variant_frame,
    load_governed_text_metadata,
    summarize_keyword_coverage,
    validate_text_variant,
)

DEFAULT_BASELINE_CONFIG = Path("configs/theory_baseline.toml")
EXPECTED_SPLITS = ("train", "val", "test")
SUPPORTED_MODEL_FAMILIES = (
    "tfidf_logreg",
    "tfidf_char_wb_logreg",
    "tfidf_svd_logreg",
    "sentence_transformer_logreg",
)


class SentenceTransformerEncoder(BaseEstimator, TransformerMixin):
    """Lazy sentence-transformer wrapper that remains joblib-serializable."""

    def __init__(
        self,
        model_name: str,
        *,
        device: str | None = None,
        batch_size: int = 32,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        model = self._load_model()
        values = X.tolist() if hasattr(X, "tolist") else list(X)
        texts = [str(item) for item in values]
        return model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

    def __getstate__(self) -> dict[str, object]:
        state = self.__dict__.copy()
        state["_model"] = None
        return state

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required for model_family="
                    "`sentence_transformer_logreg`."
                ) from exc
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device or _auto_sentence_device(),
            )
        return self._model


@dataclass(frozen=True)
class TheoryTrainingSettings:
    max_features: int
    ngram_min: int
    ngram_max: int
    min_df: int
    max_iter: int
    class_weight: str | dict[str, float] | None
    random_state: int
    char_ngram_min: int
    char_ngram_max: int
    svd_components: int
    sentence_transformer_model_name: str | None
    sentence_batch_size: int


@dataclass(frozen=True)
class TheoryEvaluationSettings:
    default_split: str
    required_retained_accuracy: float
    required_coverage_rate: float


@dataclass(frozen=True)
class TheoryRuntimeSettings:
    target_environment: str | None
    target_device: str | None
    runtime_budget_hours: float | None
    wsl_distribution: str | None


@dataclass(frozen=True)
class TheoryBaselineConfig:
    version: str
    config_path: Path
    taxonomy_config_path: Path
    supervision_config_path: Path
    gold_artifact_path: Path
    split_artifact_path: Path
    default_text_variant: str
    default_output_root: Path
    model_family: str
    comparison_variants: tuple[str, ...]
    training: TheoryTrainingSettings
    evaluation: TheoryEvaluationSettings
    runtime: TheoryRuntimeSettings
    trusted_experiment_artifact_path: Path | None
    trusted_production_artifact_path: Path | None
    baseline_anchor_run_dir: Path | None
    baseline_anchor_predictions_path: Path | None
    candidate_model_families: tuple[str, ...]


@dataclass(frozen=True)
class TheoryDataset:
    rows: pd.DataFrame
    split_version: str
    split_seed: int
    label_order: tuple[str, ...]
    label_lookup: dict[str, str]

    def rows_for_split(self, split_name: str) -> pd.DataFrame:
        normalized_split = split_name.strip().lower()
        if normalized_split == "all":
            return self.rows.copy()
        if normalized_split not in EXPECTED_SPLITS:
            raise ValueError(
                f"Unsupported split `{split_name}`. "
                f"Expected one of: {', '.join((*EXPECTED_SPLITS, 'all'))}."
            )
        return self.rows.loc[self.rows["split"] == normalized_split].copy()


@dataclass(frozen=True)
class TheoryRunArtifacts:
    run_dir: Path
    manifest_path: Path
    model_path: Path
    keyword_coverage_path: Path


def load_theory_baseline_config(
    path: str | Path = DEFAULT_BASELINE_CONFIG,
    *,
    root: Path | None = None,
) -> TheoryBaselineConfig:
    project_root = root or ROOT
    config_path = resolve_project_path(path, root=project_root)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    training_data = data.get("training", {})
    evaluation_data = data.get("evaluation", {})
    default_text_variant = validate_text_variant(str(data["default_text_variant"]))
    comparison_variants = tuple(
        validate_text_variant(str(item)) for item in data.get("comparison_variants", [])
    )
    if not comparison_variants:
        raise ValueError("Theory baseline config must declare comparison_variants.")
    model_family = validate_model_family(str(data["model_family"]))
    runtime_data = data.get("runtime", {})
    candidate_model_families = tuple(
        validate_model_family(str(item))
        for item in data.get("candidate_model_families", [])
    )

    return TheoryBaselineConfig(
        version=str(data.get("version", "")),
        config_path=config_path,
        taxonomy_config_path=resolve_project_path(data["taxonomy_config"], root=project_root),
        supervision_config_path=resolve_project_path(
            data["supervision_config"],
            root=project_root,
        ),
        gold_artifact_path=resolve_project_path(data["gold_artifact"], root=project_root),
        split_artifact_path=resolve_project_path(data["split_artifact"], root=project_root),
        default_text_variant=default_text_variant,
        default_output_root=resolve_project_path(
            data["default_output_root"],
            root=project_root,
        ),
        model_family=model_family,
        comparison_variants=comparison_variants,
        training=TheoryTrainingSettings(
            max_features=int(training_data["max_features"]),
            ngram_min=int(training_data["ngram_min"]),
            ngram_max=int(training_data["ngram_max"]),
            min_df=int(training_data["min_df"]),
            max_iter=int(training_data["max_iter"]),
            class_weight=_optional_string(training_data.get("class_weight")),
            random_state=int(training_data["random_state"]),
            char_ngram_min=int(training_data.get("char_ngram_min", 3)),
            char_ngram_max=int(training_data.get("char_ngram_max", 5)),
            svd_components=int(training_data.get("svd_components", 256)),
            sentence_transformer_model_name=_optional_string(
                training_data.get("sentence_transformer_model_name")
            ),
            sentence_batch_size=int(training_data.get("sentence_batch_size", 32)),
        ),
        evaluation=TheoryEvaluationSettings(
            default_split=str(evaluation_data["default_split"]).strip().lower(),
            required_retained_accuracy=float(
                evaluation_data.get("required_retained_accuracy", 0.70)
            ),
            required_coverage_rate=float(
                evaluation_data.get("required_coverage_rate", 0.15)
            ),
        ),
        runtime=TheoryRuntimeSettings(
            target_environment=_optional_string(runtime_data.get("target_environment")),
            target_device=_optional_string(runtime_data.get("target_device")),
            runtime_budget_hours=_optional_float(runtime_data.get("runtime_budget_hours")),
            wsl_distribution=_optional_string(runtime_data.get("wsl_distribution")),
        ),
        trusted_experiment_artifact_path=_optional_resolved_path(
            data.get("trusted_experiment_artifact"),
            root=project_root,
        ),
        trusted_production_artifact_path=_optional_resolved_path(
            data.get("trusted_production_artifact"),
            root=project_root,
        ),
        baseline_anchor_run_dir=_optional_resolved_path(
            data.get("baseline_anchor_run_dir"),
            root=project_root,
        ),
        baseline_anchor_predictions_path=_optional_resolved_path(
            data.get("baseline_anchor_predictions"),
            root=project_root,
        ),
        candidate_model_families=candidate_model_families,
    )


def load_theory_dataset(
    config: TheoryBaselineConfig,
    *,
    root: Path | None = None,
) -> TheoryDataset:
    project_root = root or ROOT
    taxonomy = load_taxonomy(config.taxonomy_config_path, root=project_root)
    label_order = tuple(taxonomy_class.identifier for taxonomy_class in taxonomy.classes)
    label_lookup = {
        taxonomy_class.identifier: taxonomy_class.label
        for taxonomy_class in taxonomy.classes
    }

    gold_rows = pd.read_csv(config.gold_artifact_path)
    split_rows = pd.read_csv(config.split_artifact_path)
    _validate_required_columns(
        gold_rows,
        {
            "record_id",
            "source_dataset",
            "source_sheet",
            "title",
            "abstract",
            "year",
            "doi",
            "label_original",
            "label_canonica",
            "canonical_id",
        },
        "gold artifact",
    )
    _validate_required_columns(
        split_rows,
        {
            "record_id",
            "split",
            "split_version",
            "split_seed",
            "same_article_group",
        },
        "split artifact",
    )
    _validate_record_ids(gold_rows, "gold artifact")
    _validate_record_ids(split_rows, "split artifact")

    gold_ids = set(gold_rows["record_id"].tolist())
    split_ids = set(split_rows["record_id"].tolist())
    if gold_ids != split_ids:
        missing_in_split = sorted(gold_ids - split_ids)
        missing_in_gold = sorted(split_ids - gold_ids)
        raise ValueError(
            "Gold and split artifacts must contain the same record ids. "
            f"Missing in split: {missing_in_split[:5]}; "
            f"missing in gold: {missing_in_gold[:5]}."
        )

    merged = gold_rows.merge(
        split_rows.loc[
            :,
            ["record_id", "split", "split_version", "split_seed", "same_article_group"],
        ],
        on="record_id",
        how="left",
        validate="one_to_one",
    )
    if merged["split"].isna().any():
        missing_ids = merged.loc[merged["split"].isna(), "record_id"].tolist()
        raise ValueError(
            "Every gold row must resolve to a split assignment. "
            f"Missing: {missing_ids[:5]}"
        )

    merged["split"] = merged["split"].map(str).str.strip().str.lower()
    invalid_splits = sorted(set(merged["split"]) - set(EXPECTED_SPLITS))
    if invalid_splits:
        raise ValueError(
            f"Unexpected split names in split artifact: {', '.join(invalid_splits)}."
        )

    missing_labels = merged["canonical_id"].isna() | (
        merged["canonical_id"].map(str).str.strip() == ""
    )
    if missing_labels.any():
        missing_ids = merged.loc[missing_labels, "record_id"].tolist()
        raise ValueError(
            "Every supervised row must resolve to one canonical label. "
            f"Missing labels for: {missing_ids[:5]}"
        )

    unexpected_labels = sorted(set(merged["canonical_id"]) - set(label_order))
    if unexpected_labels:
        raise ValueError(
            "Gold artifact contains canonical ids outside the taxonomy contract: "
            f"{unexpected_labels}."
        )

    split_versions = tuple(sorted(set(merged["split_version"].tolist())))
    split_seeds = tuple(sorted(set(int(value) for value in merged["split_seed"].tolist())))
    if len(split_versions) != 1 or len(split_seeds) != 1:
        raise ValueError(
            "Split artifact must contain exactly one split_version and one split_seed."
        )

    merged = merged.sort_values(by=["split", "record_id"]).reset_index(drop=True)
    return TheoryDataset(
        rows=merged,
        split_version=split_versions[0],
        split_seed=split_seeds[0],
        label_order=label_order,
        label_lookup=label_lookup,
    )


def train_theory_baseline(
    *,
    config: TheoryBaselineConfig,
    run_id: str,
    output_dir: str | Path | None = None,
    text_variant: str | None = None,
    root: Path | None = None,
) -> TheoryRunArtifacts:
    project_root = root or ROOT
    effective_variant = validate_text_variant(text_variant or config.default_text_variant)
    dataset = load_theory_dataset(config, root=project_root)
    text_metadata = load_governed_text_metadata(
        root=project_root,
        supervision_config_path=config.supervision_config_path,
    )
    train_rows = build_text_variant_frame(
        dataset.rows_for_split("train"),
        text_variant=effective_variant,
        text_metadata=text_metadata,
    )
    full_variant_rows = build_text_variant_frame(
        dataset.rows,
        text_variant=effective_variant,
        text_metadata=text_metadata,
    )
    keyword_coverage = summarize_keyword_coverage(
        full_variant_rows,
        text_variant=effective_variant,
    )

    pipeline = _build_training_pipeline(config)
    pipeline.fit(train_rows["text_input"], train_rows["canonical_id"])

    run_dir = resolve_run_dir(
        config=config,
        run_id=run_id,
        output_dir=output_dir,
        root=project_root,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    model_path = run_dir / "model.joblib"
    manifest_path = run_dir / "run_manifest.json"
    keyword_coverage_path = run_dir / "keyword_coverage.json"

    joblib.dump(pipeline, model_path)
    keyword_coverage_path.write_text(
        json.dumps(keyword_coverage.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    manifest = _build_run_manifest(
        config=config,
        dataset=dataset,
        run_id=run_id,
        run_dir=run_dir,
        model_path=model_path,
        keyword_coverage_path=keyword_coverage_path,
        text_variant=effective_variant,
        keyword_coverage=keyword_coverage,
        train_rows=train_rows,
        root=project_root,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return TheoryRunArtifacts(
        run_dir=run_dir,
        manifest_path=manifest_path,
        model_path=model_path,
        keyword_coverage_path=keyword_coverage_path,
    )


def train_theory_gold_plus_pseudo(
    *,
    config_path: str | Path,
    run_id: str,
    output_dir: str | Path | None = None,
    text_variant: str | None = None,
    root: Path | None = None,
    emit_comparison_bundle: bool = True,
) -> TheoryRunArtifacts:
    """Train with gold rows plus admitted pseudo-label rows (train split only, sample-weighted)."""
    project_root = root or ROOT
    resolved_config = resolve_project_path(config_path, root=project_root)
    full = tomllib.loads(resolved_config.read_text(encoding="utf-8"))
    pt = full.get("pseudo_training", {})
    if str(pt.get("training_mode", "")).strip().lower() != "gold_plus_pseudo":
        raise ValueError("pseudo_training.training_mode must be `gold_plus_pseudo` for this entrypoint.")
    pseudo_path = resolve_project_path(pt["pseudo_admitted_csv"], root=project_root)
    gold_weight = float(pt.get("gold_weight", 1.0))
    pseudo_weight = float(pt.get("pseudo_weight", 0.35))
    wave_id = str(full.get("pseudo_label_wave_id", "wave_01_conservative"))
    teacher_id = str(full.get("teacher_run_id", "sentence_transformer_logreg_test"))

    config = load_theory_baseline_config(resolved_config, root=project_root)
    effective_variant = validate_text_variant(text_variant or config.default_text_variant)
    dataset = load_theory_dataset(config, root=project_root)
    text_metadata = load_governed_text_metadata(
        root=project_root,
        supervision_config_path=config.supervision_config_path,
    )

    gold_train = dataset.rows_for_split("train")
    gold_train_variant = build_text_variant_frame(
        gold_train,
        text_variant=effective_variant,
        text_metadata=text_metadata,
    )

    pseudo_raw = pd.read_csv(pseudo_path)
    val_test_ids = set(
        dataset.rows.loc[dataset.rows["split"].astype(str).str.lower().isin(("val", "test")), "record_id"]
        .astype(str)
    )
    pseudo_raw = pseudo_raw.loc[~pseudo_raw["record_id"].astype(str).isin(val_test_ids)].copy()
    pseudo_raw["split"] = "train"
    pseudo_variant = build_text_variant_frame(
        pseudo_raw,
        text_variant=effective_variant,
        text_metadata=text_metadata,
    )

    combined = pd.concat([gold_train_variant, pseudo_variant], axis=0, ignore_index=True)
    weights = [gold_weight] * len(gold_train_variant) + [pseudo_weight] * len(pseudo_variant)
    sample_weight = pd.Series(weights, dtype="float64")

    pipeline = _build_training_pipeline(config)
    pipeline.fit(
        combined["text_input"],
        combined["canonical_id"],
        classifier__sample_weight=sample_weight.to_numpy(),
    )

    run_dir = resolve_run_dir(
        config=config,
        run_id=run_id,
        output_dir=output_dir,
        root=project_root,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    model_path = run_dir / "model.joblib"
    manifest_path = run_dir / "run_manifest.json"
    keyword_coverage_path = run_dir / "keyword_coverage.json"

    joblib.dump(pipeline, model_path)
    full_variant_rows = build_text_variant_frame(
        dataset.rows,
        text_variant=effective_variant,
        text_metadata=text_metadata,
    )
    keyword_coverage = summarize_keyword_coverage(
        full_variant_rows,
        text_variant=effective_variant,
    )
    keyword_coverage_path.write_text(
        json.dumps(keyword_coverage.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    manifest = _build_run_manifest(
        config=config,
        dataset=dataset,
        run_id=run_id,
        run_dir=run_dir,
        model_path=model_path,
        keyword_coverage_path=keyword_coverage_path,
        text_variant=effective_variant,
        keyword_coverage=keyword_coverage,
        train_rows=combined,
        root=project_root,
    )
    manifest["pseudo_label_training"] = {
        "gold_train_rows": int(len(gold_train_variant)),
        "pseudo_train_rows": int(len(pseudo_variant)),
        "gold_weight": gold_weight,
        "pseudo_weight": pseudo_weight,
        "teacher_run_id": teacher_id,
        "pseudo_label_wave_id": wave_id,
        "pseudo_admitted_csv": str(pseudo_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    training_manifest = {
        "gold_train_rows": int(len(gold_train_variant)),
        "pseudo_train_rows": int(len(pseudo_variant)),
        "gold_weight": gold_weight,
        "pseudo_weight": pseudo_weight,
        "teacher_run_id": teacher_id,
        "pseudo_label_wave_id": wave_id,
    }
    bundle_dir = pseudo_path.parent
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "pseudo_label_training_manifest.json").write_text(
        json.dumps(training_manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if emit_comparison_bundle:
        from .pseudo_label_eval import persist_phase9_pseudo_label_bundle

        persist_phase9_pseudo_label_bundle(
            root=project_root,
            full_config_path=resolved_config,
            challenger_run_dir=run_dir,
            bundle_dir=bundle_dir,
        )

    return TheoryRunArtifacts(
        run_dir=run_dir,
        manifest_path=manifest_path,
        model_path=model_path,
        keyword_coverage_path=keyword_coverage_path,
    )


def resolve_run_dir(
    *,
    config: TheoryBaselineConfig,
    run_id: str,
    output_dir: str | Path | None,
    root: Path | None = None,
) -> Path:
    project_root = root or ROOT
    if output_dir is not None:
        candidate = Path(output_dir)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        return candidate.resolve()
    return (config.default_output_root / run_id).resolve()


def with_model_family(
    config: TheoryBaselineConfig,
    model_family: str,
) -> TheoryBaselineConfig:
    return replace(config, model_family=validate_model_family(model_family))


def with_training_class_weight(
    config: TheoryBaselineConfig,
    class_weight: str | dict[str, float] | None,
) -> TheoryBaselineConfig:
    return replace(
        config,
        training=replace(config.training, class_weight=class_weight),
    )


def build_capped_balanced_class_weight(
    dataset: TheoryDataset,
    *,
    cap_multiplier: float = 3.0,
    split_name: str = "train",
) -> dict[str, float]:
    split_rows = dataset.rows_for_split(split_name)
    counts = (
        split_rows.groupby("canonical_id").size().reindex(dataset.label_order, fill_value=0)
    )
    nonzero_counts = counts.loc[counts > 0]
    if nonzero_counts.empty:
        raise ValueError("Cannot build capped class weights from an empty split.")

    total_rows = int(nonzero_counts.sum())
    class_count = int(len(nonzero_counts))
    raw_weights = {
        canonical_id: total_rows / (class_count * int(count))
        for canonical_id, count in nonzero_counts.items()
    }
    median_weight = pd.Series(list(raw_weights.values()), dtype="float64").median()
    capped_limit = float(median_weight) * float(cap_multiplier)
    return {
        canonical_id: float(min(weight, capped_limit))
        for canonical_id, weight in raw_weights.items()
    }


def load_run_manifest(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Run manifest not found at {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def load_trained_pipeline(run_dir: Path) -> Pipeline:
    model_path = run_dir / "model.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Trained model not found at {model_path}")
    return joblib.load(model_path)


def _build_training_pipeline(config: TheoryBaselineConfig) -> Pipeline:
    settings = config.training
    family = config.model_family
    classifier = LogisticRegression(
        max_iter=settings.max_iter,
        class_weight=settings.class_weight,
        random_state=settings.random_state,
    )

    if family == "tfidf_logreg":
        return Pipeline(
            steps=[
                (
                    "vectorizer",
                    TfidfVectorizer(
                        lowercase=True,
                        ngram_range=(settings.ngram_min, settings.ngram_max),
                        max_features=settings.max_features,
                        min_df=settings.min_df,
                        sublinear_tf=True,
                    ),
                ),
                ("classifier", classifier),
            ]
        )

    if family == "tfidf_char_wb_logreg":
        return Pipeline(
            steps=[
                (
                    "vectorizer",
                    TfidfVectorizer(
                        lowercase=True,
                        analyzer="char_wb",
                        ngram_range=(settings.char_ngram_min, settings.char_ngram_max),
                        max_features=settings.max_features,
                        min_df=settings.min_df,
                        sublinear_tf=True,
                    ),
                ),
                ("classifier", classifier),
            ]
        )

    if family == "tfidf_svd_logreg":
        return Pipeline(
            steps=[
                (
                    "vectorizer",
                    TfidfVectorizer(
                        lowercase=True,
                        ngram_range=(settings.ngram_min, settings.ngram_max),
                        max_features=settings.max_features,
                        min_df=settings.min_df,
                        sublinear_tf=True,
                    ),
                ),
                (
                    "svd",
                    TruncatedSVD(
                        n_components=settings.svd_components,
                        random_state=settings.random_state,
                    ),
                ),
                ("normalizer", Normalizer(copy=False)),
                ("classifier", classifier),
            ]
        )

    if family == "sentence_transformer_logreg":
        model_name = (
            settings.sentence_transformer_model_name
            or "sentence-transformers/all-MiniLM-L6-v2"
        )
        return Pipeline(
            steps=[
                (
                    "encoder",
                    SentenceTransformerEncoder(
                        model_name=model_name,
                        device=config.runtime.target_device,
                        batch_size=settings.sentence_batch_size,
                    ),
                ),
                ("classifier", classifier),
            ]
        )

    raise ValueError(f"Unsupported model family: {family}")


def _build_run_manifest(
    *,
    config: TheoryBaselineConfig,
    dataset: TheoryDataset,
    run_id: str,
    run_dir: Path,
    model_path: Path,
    keyword_coverage_path: Path,
    text_variant: str,
    keyword_coverage: Any,
    train_rows: pd.DataFrame,
    root: Path,
) -> dict[str, object]:
    train_label_counts = (
        train_rows.groupby("canonical_id").size().reindex(dataset.label_order, fill_value=0)
    )
    return {
        "run_id": run_id,
        "config_version": config.version,
        "model_family": config.model_family,
        "model_class": "sklearn.pipeline.Pipeline",
        "text_variant": text_variant,
        "training_split": "train",
        "split_version": dataset.split_version,
        "split_seed": dataset.split_seed,
        "inputs": {
            "config_path": _relative_path(config.config_path, root),
            "taxonomy_config": _relative_path(config.taxonomy_config_path, root),
            "supervision_config": _relative_path(config.supervision_config_path, root),
            "gold_artifact": _relative_path(config.gold_artifact_path, root),
            "split_artifact": _relative_path(config.split_artifact_path, root),
        },
        "config_snapshot": {
            "default_text_variant": config.default_text_variant,
            "comparison_variants": list(config.comparison_variants),
            "candidate_model_families": list(config.candidate_model_families),
            "training": {
                "max_features": config.training.max_features,
                "ngram_min": config.training.ngram_min,
                "ngram_max": config.training.ngram_max,
                "min_df": config.training.min_df,
                "max_iter": config.training.max_iter,
                "class_weight": config.training.class_weight,
                "random_state": config.training.random_state,
                "char_ngram_min": config.training.char_ngram_min,
                "char_ngram_max": config.training.char_ngram_max,
                "svd_components": config.training.svd_components,
                "sentence_transformer_model_name": config.training.sentence_transformer_model_name,
                "sentence_batch_size": config.training.sentence_batch_size,
            },
            "evaluation": {
                "default_split": config.evaluation.default_split,
                "required_retained_accuracy": config.evaluation.required_retained_accuracy,
                "required_coverage_rate": config.evaluation.required_coverage_rate,
            },
            "runtime": {
                "target_environment": config.runtime.target_environment,
                "target_device": config.runtime.target_device,
                "runtime_budget_hours": config.runtime.runtime_budget_hours,
                "wsl_distribution": config.runtime.wsl_distribution,
            },
        },
        "label_order": list(dataset.label_order),
        "label_lookup": [
            {
                "canonical_id": canonical_id,
                "label_canonica": dataset.label_lookup[canonical_id],
            }
            for canonical_id in dataset.label_order
        ],
        "training_label_counts": {
            canonical_id: int(train_label_counts[canonical_id])
            for canonical_id in dataset.label_order
        },
        "keyword_coverage": keyword_coverage.to_dict(),
        "artifacts": {
            "model": model_path.name,
            "keyword_coverage": keyword_coverage_path.name,
            "metrics_overall": "metrics_overall.json",
            "metrics_per_class": "metrics_per_class.csv",
            "confusion_matrix": "confusion_matrix.csv",
            "predictions": "predictions.csv",
            "operational_predictions": "operational_predictions.csv",
            "operational_summary": "operational_summary.json",
            "variant_comparison": "variant_comparison.csv",
            "experiment_comparison": "experiment_comparison.csv",
            "experiment_per_class_metrics": "experiment_per_class_metrics.csv",
            "champion_summary": "champion_summary.json",
        },
        "phase7_inputs": {
            "trusted_experiment_artifact": (
                _relative_path(config.trusted_experiment_artifact_path, root)
                if config.trusted_experiment_artifact_path is not None
                else None
            ),
            "trusted_production_artifact": (
                _relative_path(config.trusted_production_artifact_path, root)
                if config.trusted_production_artifact_path is not None
                else None
            ),
            "baseline_anchor_run_dir": (
                _relative_path(config.baseline_anchor_run_dir, root)
                if config.baseline_anchor_run_dir is not None
                else None
            ),
            "baseline_anchor_predictions": (
                _relative_path(config.baseline_anchor_predictions_path, root)
                if config.baseline_anchor_predictions_path is not None
                else None
            ),
        },
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "sklearn_version": sklearn.__version__,
            "target_environment": config.runtime.target_environment,
            "target_device": config.runtime.target_device,
            "runtime_budget_hours": config.runtime.runtime_budget_hours,
            "wsl_distribution": config.runtime.wsl_distribution,
            "resolved_compute_device": _resolved_compute_device(config),
            "torch_cuda_available": _torch_cuda_available(),
        },
        "run_directory": _relative_path(run_dir, root),
    }


def _validate_required_columns(
    frame: pd.DataFrame,
    required_columns: set[str],
    label: str,
) -> None:
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError(f"{label} is missing required columns: {missing_columns}")


def _validate_record_ids(frame: pd.DataFrame, label: str) -> None:
    missing_record_ids = frame["record_id"].isna() | (frame["record_id"].map(str).str.strip() == "")
    if missing_record_ids.any():
        raise ValueError(f"{label} contains rows with missing record_id values.")
    if frame["record_id"].duplicated().any():
        duplicates = frame.loc[frame["record_id"].duplicated(), "record_id"].tolist()
        raise ValueError(f"{label} contains duplicate record_id values: {duplicates[:5]}")


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_resolved_path(value: object, *, root: Path) -> Path | None:
    path_value = _optional_string(value)
    if path_value is None:
        return None
    return resolve_project_path(path_value, root=root)


def validate_model_family(model_family: str) -> str:
    normalized = model_family.strip()
    if normalized not in SUPPORTED_MODEL_FAMILIES:
        raise ValueError(
            f"Unsupported model family `{model_family}`. "
            f"Expected one of: {', '.join(SUPPORTED_MODEL_FAMILIES)}."
        )
    return normalized


def _auto_sentence_device() -> str:
    if _torch_cuda_available():
        return "cuda"
    return "cpu"


def _torch_cuda_available() -> bool:
    try:
        import torch
    except ImportError:
        return False
    return bool(torch.cuda.is_available())


def _resolved_compute_device(config: TheoryBaselineConfig) -> str:
    if config.model_family == "sentence_transformer_logreg":
        return config.runtime.target_device or _auto_sentence_device()
    return "cpu"


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
