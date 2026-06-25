from __future__ import annotations

import json
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from .input_manifest import load_structured_effect_table
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .meta_analysis import (
    dersimonian_laird as _dersimonian_laird,
    leave_one_out_meta_influence as _leave_one_out_meta_influence,
    layered_evidence_sensitivity as _layered_evidence_sensitivity,
    missing_variance_sensitivity as _missing_variance_sensitivity,
    meta_regression_moderator as _meta_regression_moderator,
    paule_mandel_hartung_knapp as _paule_mandel_hartung_knapp,
)

__all__ = [
    "_canonical_trial_ids",
    "_microbial_comparison_mask",
    "_primary_study_title_mask",
    "_dersimonian_laird",
    "_leave_one_out_meta_influence",
    "_layered_evidence_sensitivity",
    "_missing_variance_sensitivity",
    "_meta_regression_moderator",
    "_paule_mandel_hartung_knapp",
]


KNOWN_TRIAL_ALIASES = {
    "PMID:32615727": "DOI:10.3803/EnM.2020.35.2.425",
}


def _canonical_trial_ids(data: pd.DataFrame) -> pd.Series:
    """Return one analysis ID for duplicate publications of the same trial."""
    study_ids = data["study_id"].fillna("").astype(str)
    canonical = study_ids.map(lambda value: KNOWN_TRIAL_ALIASES.get(value, value))
    canonical = canonical.str.replace(
        r"^EUROPEPMC:(\d+)$", r"PMID:\1", regex=True, case=False
    )
    if "source_title" not in data:
        return canonical

    normalized_title = (
        data["source_title"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.replace(r"[^a-z0-9]+", " ", regex=True)
        .str.strip()
    )
    specific = normalized_title.str.len().ge(40)
    title_map: dict[str, str] = {}
    title_rows = pd.DataFrame(
        {"title": normalized_title[specific], "canonical": canonical[specific]}
    )
    for title, values in title_rows.groupby("title")["canonical"]:
        unique = sorted(set(values), key=lambda value: (not value.startswith("PMID:"), value))
        title_map[title] = unique[0]
    return pd.Series(
        [title_map.get(title, value) for title, value in zip(normalized_title, canonical)],
        index=data.index,
        dtype=object,
    )


def _microbial_comparison_mask(data: pd.DataFrame) -> pd.Series:
    """Reject outcome rows whose actual contrast is clearly non-microbial."""
    comparison = data.get(
        "comparison", pd.Series("", index=data.index, dtype=object)
    ).fillna("").astype(str).str.lower()
    microbial = comparison.str.contains(
        r"probiotic|synbiotic|postbiotic|microbial|akkermansia|bifidobacter|"
        r"lactobac|lacticaseibac|lactiplantibac|bacillus|cjls\d|b420|bb536|mcc\d",
        regex=True,
    )
    clearly_non_microbial = comparison.str.contains(
        r"whey|exercise|usual lifestyle|energy[-_ ]restriction(?:[-_ ]plus[-_ ]exercise)?",
        regex=True,
    )
    return ~clearly_non_microbial | microbial


def _primary_study_title_mask(data: pd.DataFrame) -> pd.Series:
    """Exclude review-level publications from intervention-effect analyses."""
    title = data.get(
        "source_title", pd.Series("", index=data.index, dtype=object)
    ).fillna("").astype(str)
    return ~title.str.contains(
        r"systematic review|meta-analysis|scoping review", case=False, regex=True
    )


ARM_FIELDS = [
    "study_id",
    "evidence_id",
    "arm_id",
    "arm_role",
    "arm_label",
    "intervention_class",
    "species",
    "strain",
    "total_cfu_per_day",
    "log10_cfu_per_day",
    "prebiotic_type",
    "prebiotic_dose_g_day",
    "duration_weeks",
    "dosage_form",
    "sample_size",
    "arm_data_status",
    "source_title",
]

EFFECT_FIELDS = [
    "effect_id",
    "study_id",
    "evidence_id",
    "outcome_domain",
    "effect_measure",
    "estimate",
    "standard_error",
    "variance",
    "variance_provenance",
    "ci_lower",
    "ci_upper",
    "effect_unit",
    "intervention_mean",
    "intervention_sd",
    "intervention_n",
    "control_mean",
    "control_sd",
    "control_n",
    "intervention_arm_id",
    "control_arm_id",
    "comparison",
    "time_point",
    "sample_size_total",
    "extraction_method",
    "validation_ready",
    "confidence",
    "source_final_value",
]


@dataclass(frozen=True)
class ArmDatasetResult:
    output_path: Path
    studies: int
    arms: int


@dataclass(frozen=True)
class ContinuousEffectResult:
    output_path: Path
    effects: int
    validation_ready_effects: int


@dataclass(frozen=True)
class ContinuousModelResult:
    metrics_output: Path
    predictions_output: Path
    model_output: Path
    modeled_strata: int


def build_arm_level_dataset(
    review_paths: list[Path],
    intervention_review_paths: list[Path],
    output_path: Path,
    target_studies: int = 80,
    structured_paths: list[Path] | None = None,
) -> ArmDatasetResult:
    if target_studies < 1:
        raise ValueError("target_studies must be at least 1")
    reviews = _load_reviews(review_paths)
    n_lookup = _sample_size_lookup(reviews)
    microbial = reviews[_microbial_mask(reviews)].copy()
    microbial["_status_score"] = (
        microbial.get("review_status", "").fillna("").astype(str).str.lower().eq("extracted").astype(int) * 100
    )
    richness_fields = [
        "comparison",
        "sample_size_confirmed",
        "time_point",
        "second_pass_arm_terms",
        "second_pass_intervention_snippets",
        "pdf_deep_methods_excerpt",
    ]
    microbial["_richness"] = sum(
        microbial.get(field, pd.Series(index=microbial.index, dtype=object)).notna().astype(int)
        for field in richness_fields
    )
    study_rank = (
        microbial.groupby("evidence_id", as_index=False)
        .agg(
            status_score=("_status_score", "max"),
            richness=("_richness", "max"),
            outcome_count=("outcome_domain", "nunique"),
        )
        .sort_values(
            ["status_score", "richness", "outcome_count", "evidence_id"],
            ascending=[False, False, False, True],
        )
    )
    selected = study_rank.head(target_studies)["evidence_id"].tolist()
    # Studies that contribute curated numeric effects must appear in the arm
    # registry so the training merge (effects x arms on study_id) keeps them.
    structured_meta = _structured_study_meta(structured_paths or [])
    if not structured_meta and len(selected) < target_studies:
        raise ValueError(
            f"Only {len(selected)} microbial studies are available; target is {target_studies}."
        )
    study_order = list(dict.fromkeys(selected + list(structured_meta)))

    interventions = _load_interventions(intervention_review_paths)
    rows: list[dict[str, object]] = []
    for evidence_id in study_order:
        study_rows = microbial[microbial["evidence_id"] == evidence_id]
        meta = structured_meta.get(evidence_id, {})
        if len(study_rows):
            representative = study_rows.sort_values(
                ["_status_score", "_richness"], ascending=False
            ).iloc[0]
            comparison = _text(representative.get("comparison")) or meta.get("comparison", "")
            sample_size = _sample_size(representative.get("sample_size_confirmed"))
            duration = _duration_weeks(representative.get("time_point"))
            source_title = _text(representative.get("title")) or meta.get("title", "")
            extracted = str(representative.get("review_status", "")).lower() == "extracted"
        else:
            # structured-only study: derive arm context from the curated effect table
            representative = pd.Series({"title": meta.get("title", "")})
            comparison = meta.get("comparison", "")
            sample_size = None
            duration = None
            source_title = meta.get("title", "")
            extracted = True  # curated numeric effect counts as confirmed data
        if sample_size is None:
            sample_size = n_lookup.get(evidence_id)
        active_label, control_label = _arm_labels(comparison, representative)
        intervention = interventions.get(evidence_id, {})
        confirmed_duration = _number(intervention.get("final_duration_weeks"))
        if confirmed_duration is not None:
            duration = confirmed_duration
        active_class = _intervention_class(active_label)
        # branded/strain-coded arms (e.g. "SF68", "WLM3P", "K56") miss the generic
        # keyword; an extracted probiotic species/strain confirms a microbial arm.
        if active_class == "other" and (
            _text(intervention.get("final_species")) or _text(intervention.get("final_strain"))
        ):
            active_class = "synbiotic" if _text(intervention.get("final_prebiotic_type")) else "probiotic"
        active_id = f"{evidence_id}::arm:intervention"
        control_id = f"{evidence_id}::arm:control"
        rows.append(
            {
                "study_id": evidence_id,
                "evidence_id": evidence_id,
                "arm_id": active_id,
                "arm_role": "intervention",
                "arm_label": active_label,
                "intervention_class": active_class,
                "species": _text(intervention.get("final_species")),
                "strain": _text(intervention.get("final_strain")),
                "total_cfu_per_day": _number(intervention.get("final_total_CFU_per_day")),
                "log10_cfu_per_day": _number(intervention.get("final_log10_CFU_per_day")),
                "prebiotic_type": _text(intervention.get("final_prebiotic_type")),
                "prebiotic_dose_g_day": _number(
                    intervention.get("final_prebiotic_dose_g_day")
                ),
                "duration_weeks": duration,
                "dosage_form": _text(intervention.get("final_dosage_form")),
                "sample_size": sample_size,
                "arm_data_status": "partially_extracted" if extracted else "queued_for_extraction",
                "source_title": source_title,
            }
        )
        rows.append(
            {
                "study_id": evidence_id,
                "evidence_id": evidence_id,
                "arm_id": control_id,
                "arm_role": "control",
                "arm_label": control_label,
                "intervention_class": _intervention_class(control_label),
                "duration_weeks": duration,
                "sample_size": sample_size,
                "arm_data_status": "partially_extracted" if extracted else "queued_for_extraction",
                "source_title": source_title,
            }
        )

    output = pd.DataFrame(rows, columns=ARM_FIELDS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    return ArmDatasetResult(output_path, output["study_id"].nunique(), len(output))


def build_continuous_effects(
    review_paths: list[Path],
    arm_path: Path,
    output_path: Path,
    structured_paths: list[Path] | None = None,
    detail_paths: list[Path] | None = None,
    include_abstract_mined: bool = False,
) -> ContinuousEffectResult:
    reviews = _load_reviews(review_paths)
    # sample-size lookup keyed by evidence_id, used to derive standard errors from
    # p-values when an arm-specific n is unavailable. Worksheet `sample_size_confirmed`
    # takes precedence; evidence-detail enrollment / abstract "n=" fills the gaps.
    n_lookup = _detail_sample_sizes(detail_paths or [])
    n_lookup.update(_sample_size_lookup(reviews))

    extracted = reviews[
        reviews.get("review_status", "").fillna("").astype(str).str.lower().eq("extracted")
    ].copy()
    extracted = extracted.drop_duplicates(["evidence_id", "outcome_domain"], keep="last")
    arms = pd.read_csv(arm_path)
    valid_studies = set(arms["study_id"].astype(str))

    rows: list[dict[str, object]] = []
    # (1) legacy path: hand-extracted worksheet rows already in the arm registry.
    for _, row in extracted.iterrows():
        evidence_id = _text(row.get("evidence_id"))
        if evidence_id not in valid_studies:
            continue
        parsed = _parse_continuous_effect(
            _text(row.get("final_value")), _text(row.get("sample_size_confirmed"))
        )
        if parsed is None:
            continue
        rows.append(
            _effect_row(
                evidence_id=evidence_id,
                outcome_domain=_text(row.get("outcome_domain")),
                effect_unit=_text(row.get("final_unit")),
                comparison=_text(row.get("comparison")),
                time_point=_text(row.get("time_point")),
                sample_size_total=_sample_size(row.get("sample_size_confirmed")),
                parsed=parsed,
                extraction_method=parsed["extraction_method"],
                confidence="high",
                source_final_value=_text(row.get("final_value")),
            )
        )

    # (2) curated structured-effects tables (already parsed numeric effect_difference).
    rows.extend(_effects_from_structured(structured_paths or [], n_lookup))

    # (3) optional abstract supplement (lower confidence, excluded from primary model).
    if include_abstract_mined:
        rows.extend(mine_abstract_effects(detail_paths or [], n_lookup))

    # dedup per (study, domain, unit): prefer high confidence, then validation_ready.
    rows.sort(
        key=lambda r: (
            0 if r["confidence"] == "high" else 1,
            0 if r["validation_ready"] else 1,
        )
    )
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, object]] = []
    for row in rows:
        key = (str(row["study_id"]), str(row["outcome_domain"]), str(row["effect_unit"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    output = pd.DataFrame(deduped, columns=EFFECT_FIELDS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    ready = int(output["validation_ready"].sum()) if len(output) else 0
    return ContinuousEffectResult(output_path, len(output), ready)


def _effect_row(
    *,
    evidence_id: str,
    outcome_domain: str,
    effect_unit: str,
    comparison: str,
    time_point: str,
    sample_size_total: float | None,
    parsed: dict[str, object],
    extraction_method: str,
    confidence: str,
    source_final_value: str,
) -> dict[str, object]:
    se = parsed.get("standard_error")
    se_value = float(se) if isinstance(se, (int, float)) else None
    provenance_method = f"{extraction_method}_{parsed.get('extraction_method', '')}"
    variance_provenance = _variance_provenance(provenance_method, se_value)
    return {
        "effect_id": f"{evidence_id}::{outcome_domain}::{effect_unit}",
        "study_id": evidence_id,
        "evidence_id": evidence_id,
        "outcome_domain": outcome_domain,
        "effect_measure": parsed.get("effect_measure"),
        "estimate": parsed.get("estimate"),
        "standard_error": se_value,
        "variance": se_value**2 if se_value is not None else None,
        "variance_provenance": variance_provenance,
        "ci_lower": parsed.get("ci_lower"),
        "ci_upper": parsed.get("ci_upper"),
        "effect_unit": effect_unit,
        "intervention_mean": parsed.get("intervention_mean"),
        "intervention_sd": parsed.get("intervention_sd"),
        "intervention_n": parsed.get("intervention_n"),
        "control_mean": parsed.get("control_mean"),
        "control_sd": parsed.get("control_sd"),
        "control_n": parsed.get("control_n"),
        "intervention_arm_id": f"{evidence_id}::arm:intervention",
        "control_arm_id": f"{evidence_id}::arm:control",
        "comparison": comparison,
        "time_point": time_point,
        "sample_size_total": sample_size_total,
        "extraction_method": extraction_method,
        "validation_ready": bool(
            se_value is not None
            and se_value > 0
            and variance_provenance in {"reported_ci", "arm_sd_and_n"}
        ),
        "confidence": confidence,
        "source_final_value": source_final_value,
    }


OUTCOME_DOMAIN_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("BMI", ("body mass index", "bmi")),
    ("waist", ("waist circumference", "waist")),
    ("body_fat", ("body fat", "fat mass", "visceral fat", "adiposity", "vat")),
    ("weight", ("body weight", "weight loss", "weight")),
    ("glucose", ("fasting glucose", "hba1c", "insulin", "homa", "glycaemic", "glycemic")),
    ("lipid", ("triglyceride", "cholesterol", "ldl", "hdl", "lipid")),
]

EFFECT_UNIT_PATTERNS: list[tuple[str, str]] = [
    (r"kg/m\^?2|kg/m2|kg\s*m-?2", "kg/m2"),
    (r"\bcm\b", "cm"),
    (r"\bkg\b", "kg"),
    (r"%|percent", "%"),
]


def mine_abstract_effects(
    detail_paths: list[Path], n_lookup: dict[str, float]
) -> list[dict[str, object]]:
    """Auto-mine continuous effect sizes from abstracts / primary outcomes.

    Lower precision than curated extraction: every emitted row is tagged
    ``confidence="low"`` and ``extraction_method="abstract_mined"`` so the
    training step can exclude it from the primary validated model.
    """
    if not detail_paths:
        return []
    frames = [pd.read_csv(path) for path in detail_paths if Path(path).is_file()]
    if not frames:
        return []
    table = pd.concat(frames, ignore_index=True, sort=False).drop_duplicates(
        "evidence_id", keep="last"
    )
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for _, row in table.iterrows():
        evidence_id = _text(row.get("evidence_id"))
        if not evidence_id:
            continue
        text = " ".join(
            _text(row.get(field)) for field in ("abstract", "primary_outcomes", "secondary_outcomes")
        )
        if not text:
            continue
        n_total = n_lookup.get(evidence_id)
        for sentence in re.split(r"(?<=[.;])\s+", text):
            domain = _infer_outcome_domain(sentence)
            if domain is None:
                continue
            parsed = _parse_abstract_estimate(sentence, n_total)
            if parsed is None:
                continue
            unit = parsed.get("effect_unit") or _infer_effect_unit(sentence)
            key = (evidence_id, domain, str(unit))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                _effect_row(
                    evidence_id=evidence_id,
                    outcome_domain=domain,
                    effect_unit=str(unit),
                    comparison="abstract_mined",
                    time_point="",
                    sample_size_total=n_total,
                    parsed=parsed,
                    extraction_method="abstract_mined",
                    confidence="low",
                    source_final_value=sentence.strip()[:300],
                )
            )
    return rows


def _parse_abstract_estimate(sentence: str, n_total: float | None) -> dict[str, object] | None:
    """Extract an estimate (and SE when a CI/p is present) from an abstract sentence.

    Lower precision than the curated parser; used only for the low-confidence
    abstract supplement. Returns ``None`` when no estimate can be read.
    """
    # (1) curated-style "difference -X (95% CI ...)" — gives a standard error
    parsed = _parse_continuous_effect(sentence, "")
    if parsed is not None and parsed.get("standard_error"):
        return parsed

    normalized = (
        sentence.replace("−", "-").replace("–", "-").replace("—", "-")
    )
    number = r"\d+(?:\.\d+)?"
    unit_pat = r"(kg/m\^?2|kg/m2|kg|cm|%)"

    # (2) directional change: "reduced/decreased ... by X unit" (negative effect)
    decrease = re.search(
        rf"(?:reduc\w*|decreas\w*|lower\w*|loss of|declin\w*)[^.;]*?({number})\s*{unit_pat}",
        normalized,
        flags=re.IGNORECASE,
    )
    increase = re.search(
        rf"(?:increas\w*|gain\w*|rais\w*|rose|higher)[^.;]*?({number})\s*{unit_pat}",
        normalized,
        flags=re.IGNORECASE,
    )
    estimate: float | None = None
    unit = ""
    if decrease:
        estimate = -float(decrease.group(1))
        unit = _normalize_unit(decrease.group(2))
    elif increase:
        estimate = float(increase.group(1))
        unit = _normalize_unit(increase.group(2))
    if estimate is None:
        return None

    # optional SE from a p-value in the same sentence + study n
    se = None
    p_value = _p_to_float(_extract_p(normalized))
    if p_value is not None and n_total is not None and estimate != 0:
        z = NormalDist().inv_cdf(1 - p_value / 2)
        if z > 0:
            se = abs(estimate) / z
    return {
        "effect_measure": "abstract_directional_change",
        "estimate": estimate,
        "standard_error": se,
        "ci_lower": estimate - 1.96 * se if se is not None else None,
        "ci_upper": estimate + 1.96 * se if se is not None else None,
        "effect_unit": unit,
    }


def _extract_p(text: str) -> str:
    match = re.search(r"p\s*[<=]\s*0?\.\d+", text, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def _normalize_unit(raw: str) -> str:
    lowered = raw.lower().replace("^", "")
    if lowered in ("kg/m2",):
        return "kg/m2"
    return lowered


def _infer_outcome_domain(sentence: str) -> str | None:
    lowered = sentence.lower()
    for domain, keywords in OUTCOME_DOMAIN_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return domain
    return None


def _infer_effect_unit(sentence: str) -> str:
    lowered = sentence.lower()
    for pattern, unit in EFFECT_UNIT_PATTERNS:
        if re.search(pattern, lowered):
            return unit
    return "unspecified"


def _effects_from_structured(
    structured_paths: list[Path], n_lookup: dict[str, float]
) -> list[dict[str, object]]:
    if not structured_paths:
        return []
    existing = [Path(path) for path in structured_paths if Path(path).is_file()]
    if not existing:
        return []
    table = load_structured_effect_table(existing)
    rows: list[dict[str, object]] = []
    for _, row in table.iterrows():
        evidence_id = _text(row.get("evidence_id"))
        outcome_domain = _text(row.get("outcome_domain"))
        if not evidence_id or not outcome_domain:
            continue
        estimate = _number(row.get("effect_difference"))
        if estimate is None:
            intervention = _number(row.get("intervention_effect"))
            control = _number(row.get("control_effect"))
            if intervention is not None and control is not None:
                estimate = intervention - control
        if estimate is None:
            continue
        source_value = _text(row.get("source_final_value"))
        effect_unit = _text(row.get("effect_unit"))
        # 'endpoint' rows store absolute arm means; their curated effect_difference
        # has been seen corrupted by mean/SD column misalignment (e.g. a "-69.51 kg"
        # change that is really control_sd - intervention_mean). When the source
        # carries a parseable two-arm "mean +/- sd vs mean +/- sd", recompute the
        # between-arm endpoint difference from it (authoritative over the stored value).
        if "endpoint" in effect_unit.lower():
            recomputed = _two_arm_endpoint_difference(source_value)
            if recomputed is not None:
                estimate = recomputed
        # prefer a curated worksheet n; fall back to an n embedded in the row text
        n_total = n_lookup.get(evidence_id)
        if n_total is None:
            n_total = _sample_size(f"{source_value} {_text(row.get('source_note'))}")

        # Lipid rows often mash TC/LDL/HDL/TG and mix mg/dL with mmol/L into one
        # estimate, which makes the pooled lipid stratum incomparable. De-mash into
        # one row per labelled subtype (outcome_domain=lipid_<subtype>, unit mg/dL).
        if outcome_domain == "lipid":
            sub_effects = _split_lipid_into_subtypes(source_value, effect_unit)
            if sub_effects:
                between_group_p = _text(row.get("between_group_p"))
                comparison = _text(row.get("comparison"))
                for subtype, est_mgdl in sub_effects:
                    # derive SE from the row's between-group p + study n (z-test
                    # back-calculation). source_final_value is left blank so the
                    # multi-lipid CI text is not mis-parsed onto one subtype.
                    se, method = _derive_standard_error(
                        estimate=est_mgdl,
                        source_final_value=(source_value if len(sub_effects) == 1 else ""),
                        between_group_p=between_group_p,
                        n_total=n_total,
                    )
                    parsed_sub: dict[str, object] = {
                        "effect_measure": "between_group_difference",
                        "estimate": est_mgdl,
                        "standard_error": se,
                        "ci_lower": est_mgdl - 1.96 * se if se is not None else None,
                        "ci_upper": est_mgdl + 1.96 * se if se is not None else None,
                    }
                    rows.append(
                        _effect_row(
                            evidence_id=evidence_id,
                            outcome_domain=f"lipid_{subtype}",
                            effect_unit="mg/dL",
                            comparison=comparison,
                            time_point="",
                            sample_size_total=n_total,
                            parsed=parsed_sub,
                            extraction_method=f"curated_structured_effect{method}",
                            confidence="high",
                            source_final_value=source_value,
                        )
                    )
                continue

        se, method = _derive_standard_error(
            estimate=estimate,
            source_final_value=source_value,
            between_group_p=_text(row.get("between_group_p")),
            n_total=n_total,
        )
        parsed: dict[str, object] = {
            "effect_measure": "between_group_difference",
            "estimate": estimate,
            "standard_error": se,
            "ci_lower": estimate - 1.96 * se if se is not None else None,
            "ci_upper": estimate + 1.96 * se if se is not None else None,
        }
        rows.append(
            _effect_row(
                evidence_id=evidence_id,
                outcome_domain=outcome_domain,
                effect_unit=effect_unit,
                comparison=_text(row.get("comparison")),
                time_point="",
                sample_size_total=n_total,
                parsed=parsed,
                extraction_method=f"curated_structured_effect{method}",
                confidence="high",
                source_final_value=source_value,
            )
        )
    return rows


def _structured_study_meta(structured_paths: list[Path]) -> dict[str, dict[str, str]]:
    """Map evidence_id -> arm context for studies with a numeric curated effect."""
    if not structured_paths:
        return {}
    existing = [Path(path) for path in structured_paths if Path(path).is_file()]
    if not existing:
        return {}
    table = load_structured_effect_table(existing)
    meta: dict[str, dict[str, str]] = {}
    for _, row in table.iterrows():
        evidence_id = _text(row.get("evidence_id"))
        if not evidence_id:
            continue
        estimate = _number(row.get("effect_difference"))
        if estimate is None:
            intervention = _number(row.get("intervention_effect"))
            control = _number(row.get("control_effect"))
            if intervention is None or control is None:
                continue
        comparison = _text(row.get("comparison"))
        # keep the first comparison that encodes an intervention contrast
        if evidence_id not in meta or ("_vs_" in comparison and "_vs_" not in meta[evidence_id]["comparison"]):
            meta[evidence_id] = {"comparison": comparison, "title": ""}
    return meta


def _detail_sample_sizes(detail_paths: list[Path]) -> dict[str, float]:
    """Recover a study total n from evidence-detail enrollment / abstract text."""
    lookup: dict[str, float] = {}
    if not detail_paths:
        return lookup
    frames = [pd.read_csv(path) for path in detail_paths if Path(path).is_file()]
    if not frames:
        return lookup
    table = pd.concat(frames, ignore_index=True, sort=False).drop_duplicates(
        "evidence_id", keep="last"
    )
    for _, row in table.iterrows():
        evidence_id = _text(row.get("evidence_id"))
        if not evidence_id:
            continue
        size = _number(row.get("enrollment"))
        if size is None:
            size = _sample_size(
                f"{_text(row.get('abstract'))} {_text(row.get('arms'))}"
            )
        if size is not None and size > 0:
            lookup[evidence_id] = size
    return lookup


def _sample_size_lookup(reviews: pd.DataFrame) -> dict[str, float]:
    lookup: dict[str, float] = {}
    if "evidence_id" not in reviews or "sample_size_confirmed" not in reviews:
        return lookup
    for _, row in reviews.iterrows():
        evidence_id = _text(row.get("evidence_id"))
        if not evidence_id or evidence_id in lookup:
            continue
        size = _sample_size(row.get("sample_size_confirmed"))
        if size is not None:
            lookup[evidence_id] = size
    return lookup


def _derive_standard_error(
    *,
    estimate: float,
    source_final_value: str,
    between_group_p: str,
    n_total: float | None,
) -> tuple[float | None, str]:
    # (a) confidence interval present in the source text
    parsed = _parse_continuous_effect(source_final_value, source_final_value)
    if parsed is not None and parsed.get("standard_error"):
        provenance = str(parsed.get("extraction_method", ""))
        suffix = "_arm_sd" if provenance == "two_arm_mean_sd_and_arm_n" else "_ci"
        return float(parsed["standard_error"]), suffix
    # (b) two-sided p-value + total sample size -> z-test back-calculation
    p_value = _p_to_float(between_group_p)
    if p_value is not None and n_total is not None and estimate != 0:
        z = NormalDist().inv_cdf(1 - p_value / 2)
        if z > 0:
            return abs(estimate) / z, "_pbound"
    return None, "_no_se"


def _variance_provenance(extraction_method: str, se_value: float | None) -> str:
    if se_value is None or se_value <= 0:
        return "missing"
    method = extraction_method.lower()
    if "pbound" in method:
        return "pvalue_backcalculated"
    if "arm_sd" in method or "two_arm_mean_sd_and_arm_n" in method:
        return "arm_sd_and_n"
    if "ci" in method:
        return "reported_ci"
    return "unclassified_standard_error"


def _p_to_float(text: str) -> float | None:
    cleaned = _text(text).lower().replace(" ", "")
    if not cleaned:
        return None
    match = re.search(r"[<=]?(\d*\.?\d+)", cleaned)
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    if cleaned.startswith(">"):
        return None  # a p lower bound only bounds SE from below; not usable
    if not 0 < value < 1:
        return None
    return value


def random_effects_meta_analysis(
    effect_path: Path,
    arm_path: Path,
    output_path: Path,
    minimum_studies: int = 3,
) -> dict[str, object]:
    """Per-stratum random-effects meta-analysis over curated, SE-bearing effects.

    The primary estimate uses Paule-Mandel tau2 with a modified Hartung-Knapp
    small-sample interval. DerSimonian-Laird is retained as a sensitivity result.
    Only high-confidence rows with a positive standard error and a microbial
    intervention arm enter.
    """
    effects = pd.read_csv(effect_path)
    effects["confidence"] = effects.get("confidence", "high")
    effects["confidence"] = effects["confidence"].fillna("high").astype(str)
    arms = pd.read_csv(arm_path)
    if "source_title" not in arms:
        arms["source_title"] = ""
    for column in ("species", "strain", "dosage_form"):
        if column not in arms:
            arms[column] = ""
    active = arms[arms["arm_role"] == "intervention"][
        ["study_id", "intervention_class", "source_title"]
    ]
    data = effects.merge(active, on="study_id", how="left")
    data["analysis_study_id"] = _canonical_trial_ids(data)
    data = data[data["intervention_class"].isin(["probiotic", "synbiotic"])]
    data = data[_microbial_comparison_mask(data)].copy()
    data = data[_primary_study_title_mask(data)].copy()
    data = data[data["confidence"].str.lower().eq("high")].copy()
    data["estimate"] = pd.to_numeric(data["estimate"], errors="coerce")
    data["standard_error"] = pd.to_numeric(data["standard_error"], errors="coerce")
    if "variance_provenance" not in data:
        data["variance_provenance"] = [
            _variance_provenance(str(method), se if np.isfinite(se) else None)
            for method, se in zip(data["extraction_method"], data["standard_error"])
        ]
    data = data[data["estimate"].notna() & (data["standard_error"] > 0)].copy()
    data["canonical_unit"] = data["effect_unit"].map(_canonical_unit)
    data = data[~data["canonical_unit"].isin(["mixed", "unspecified"])].copy()
    data["stratum"] = data["outcome_domain"].astype(str) + "|" + data["canonical_unit"].astype(str)

    strata: list[dict[str, object]] = []
    consistent = 0
    for stratum, all_precision_group in data.groupby("stratum"):
        direct_group = all_precision_group[
            all_precision_group["variance_provenance"].isin(
                ["reported_ci", "arm_sd_and_n"]
            )
        ].copy()
        group, _ = _trim_estimate_outliers(direct_group)
        # one row per study (most precise) to keep studies independent
        group = group.sort_values("standard_error").drop_duplicates(
            "analysis_study_id", keep="first"
        )
        if group["analysis_study_id"].nunique() < minimum_studies:
            strata.append(
                {
                    "stratum": stratum,
                    "k_studies": int(group["analysis_study_id"].nunique()),
                    "pvalue_backcalculated_studies_excluded": int(
                        all_precision_group.loc[
                            all_precision_group["variance_provenance"]
                            == "pvalue_backcalculated",
                            "analysis_study_id",
                        ].nunique()
                    ),
                    "status": "insufficient_direct_variance_studies",
                }
            )
            continue
        estimates = group["estimate"].to_numpy()
        variances = (group["standard_error"] ** 2).to_numpy()
        res = _paule_mandel_hartung_knapp(estimates, variances)
        dl = _dersimonian_laird(estimates, variances)
        res["dersimonian_laird_sensitivity"] = {
            key: dl[key]
            for key in (
                "pooled_effect",
                "ci95_low",
                "ci95_high",
                "ci_excludes_zero",
                "tau2",
            )
        }
        res["stratum"] = stratum
        res["status"] = "random_effects_meta_analyzed"
        res["variance_policy"] = "reported_ci_or_arm_sd_and_n_only"
        sensitivity = all_precision_group.sort_values("standard_error").drop_duplicates(
            "analysis_study_id", keep="first"
        )
        if len(sensitivity) >= minimum_studies and len(sensitivity) > len(group):
            sensitivity_result = _paule_mandel_hartung_knapp(
                sensitivity["estimate"].to_numpy(),
                sensitivity["standard_error"].pow(2).to_numpy(),
            )
            res["pvalue_backcalculated_sensitivity"] = sensitivity_result
        transfer_interval_excludes_zero = bool(
            res.get("prediction_interval_low") is not None
            and res.get("prediction_interval_high") is not None
            and (
                float(res["prediction_interval_high"]) < 0
                or float(res["prediction_interval_low"]) > 0
            )
        )
        res["transfer_interval_excludes_zero"] = transfer_interval_excludes_zero
        res["replication_ready"] = bool(
            res["ci_excludes_zero"]
            and transfer_interval_excludes_zero
            and int(res["k_studies"]) >= 5
            and float(res["i2_percent"]) < 50
        )
        res["evidence_state"] = (
            "replication_ready_statistical_signal"
            if res["replication_ready"]
            else "statistical_interval_only_not_replication_ready"
            if res["ci_excludes_zero"]
            else "uncertain"
        )
        consistent += bool(res["ci_excludes_zero"])
        strata.append(res)

    report = {
        "model_level": "small_sample_random_effects_meta_analysis",
        "method": (
            "Paule-Mandel tau2 plus modified Hartung-Knapp-Sidik-Jonkman interval; "
            "DerSimonian-Laird retained as sensitivity; one most-precise effect per study"
        ),
        "minimum_direct_variance_studies": minimum_studies,
        "strata_meta_analyzed": sum(s.get("status") == "random_effects_meta_analyzed" for s in strata),
        "strata_with_pooled_effect_excluding_zero": consistent,
        "strata_replication_ready": sum(bool(s.get("replication_ready")) for s in strata),
        "strata": strata,
        "combination_ranking_enabled": False,
        "limitation": (
            "Primary synthesis uses only reported confidence intervals or arm SD and n. "
            "P-value-backcalculated standard errors are sensitivity-only. "
            "Internal small-sample random-effects synthesis of curated between-group effects. "
            "A pooled CI "
            "excluding zero indicates a consistent direction across these studies; it is not "
            "external/clinical validation and high I^2 signals the pooled estimate may not "
            "transfer to a new population."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def missing_variance_robustness_analysis(
    effect_path: Path,
    arm_path: Path,
    output_path: Path,
    minimum_studies: int = 3,
    bootstrap_iterations: int = 10000,
) -> dict[str, object]:
    """Triangulate effects when standard errors are structurally incomplete."""
    effects = pd.read_csv(effect_path)
    effects["confidence"] = effects.get("confidence", "high")
    effects["confidence"] = effects["confidence"].fillna("high").astype(str)
    arms = pd.read_csv(arm_path)
    if "source_title" not in arms:
        arms["source_title"] = ""
    active = arms[arms["arm_role"] == "intervention"][
        ["study_id", "intervention_class", "source_title"]
    ]
    data = effects.merge(active, on="study_id", how="left")
    data["analysis_study_id"] = _canonical_trial_ids(data)
    data = data[data["intervention_class"].isin(["probiotic", "synbiotic"])]
    data = data[_microbial_comparison_mask(data)].copy()
    data = data[_primary_study_title_mask(data)].copy()
    data = data[data["confidence"].str.lower().eq("high")].copy()
    data["estimate"] = pd.to_numeric(data["estimate"], errors="coerce")
    data["standard_error"] = pd.to_numeric(data["standard_error"], errors="coerce")
    if "variance_provenance" not in data:
        data["variance_provenance"] = [
            _variance_provenance(str(method), se if np.isfinite(se) else None)
            for method, se in zip(data["extraction_method"], data["standard_error"])
        ]
    direct_variance = data["variance_provenance"].isin(
        ["reported_ci", "arm_sd_and_n"]
    )
    data.loc[~direct_variance, "standard_error"] = np.nan
    data = data[data["estimate"].notna()].copy()
    data["canonical_unit"] = data["effect_unit"].map(_canonical_unit)
    data = data[~data["canonical_unit"].isin(["mixed", "unspecified"])].copy()
    data["stratum"] = data["outcome_domain"].astype(str) + "|" + data["canonical_unit"]

    strata: list[dict[str, object]] = []
    for index, (stratum, raw_group) in enumerate(data.groupby("stratum")):
        group, trimmed = _trim_estimate_outliers(raw_group)
        selected_rows = []
        for _, study_rows in group.groupby("analysis_study_id"):
            with_se = study_rows[study_rows["standard_error"] > 0]
            if len(with_se):
                selected_rows.append(with_se.sort_values("standard_error").iloc[0])
            else:
                row = study_rows.iloc[0].copy()
                row["estimate"] = float(study_rows["estimate"].median())
                selected_rows.append(row)
        study_group = pd.DataFrame(selected_rows)
        if len(study_group) < minimum_studies:
            strata.append(
                {
                    "stratum": stratum,
                    "k_studies": int(len(study_group)),
                    "status": "insufficient_independent_studies",
                }
            )
            continue
        variances = study_group["standard_error"].astype(float).pow(2).to_numpy()
        result = _missing_variance_sensitivity(
            study_group["estimate"].astype(float).to_numpy(),
            variances,
            bootstrap_iterations=bootstrap_iterations,
            random_seed=20260614 + index,
        )
        result.update(
            {
                "stratum": stratum,
                "status": "missing_variance_robustness_analyzed",
                "outlier_rows_trimmed": int(trimmed),
            }
        )
        strata.append(result)

    analyzed = [
        row for row in strata if row.get("status") == "missing_variance_robustness_analyzed"
    ]
    report = {
        "model_level": "missing_variance_robustness_triangulation",
        "method": (
            "Direct-variance PM/HKSJ (reported CI or arm SD+n); median- and "
            "upper-quartile-variance imputation "
            "as sensitivity analyses; study-level median bootstrap and exact sign test"
        ),
        "minimum_studies": minimum_studies,
        "bootstrap_iterations": bootstrap_iterations,
        "strata_analyzed": len(analyzed),
        "evidence_state_counts": {
            state: sum(row["evidence_state"] == state for row in analyzed)
            for state in sorted({row["evidence_state"] for row in analyzed})
        },
        "strata": strata,
        "combination_ranking_enabled": False,
        "limitation": (
            "P-value-backcalculated standard errors are treated as missing variance here. "
            "Imputed variances do not create new information and are never treated as primary "
            "evidence. Sign and median analyses ignore study precision and are used only to "
            "check whether conclusions depend entirely on variance availability."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def train_continuous_effect_models(
    effect_path: Path,
    arm_path: Path,
    metrics_output: Path,
    predictions_output: Path,
    model_output: Path,
    minimum_studies: int = 5,
    confidence_policy: str = "high_confidence_only",
) -> ContinuousModelResult:
    if confidence_policy not in ("high_confidence_only", "all"):
        raise ValueError("confidence_policy must be 'high_confidence_only' or 'all'")
    effects = pd.read_csv(effect_path)
    if "confidence" not in effects.columns:
        effects["confidence"] = "high"
    effects["confidence"] = effects["confidence"].fillna("high").astype(str)
    arms = pd.read_csv(arm_path)
    if "source_title" not in arms:
        arms["source_title"] = ""
    for column in ("species", "strain", "dosage_form"):
        if column not in arms:
            arms[column] = ""
    active = arms[arms["arm_role"] == "intervention"].copy()
    data = effects.merge(
        active[
            [
                "study_id",
                "intervention_class",
                "species",
                "strain",
                "log10_cfu_per_day",
                "duration_weeks",
                "dosage_form",
                "sample_size",
                "source_title",
            ]
        ],
        on="study_id",
        how="left",
    )
    data["analysis_study_id"] = _canonical_trial_ids(data)
    data = _add_interpretable_intervention_features(data)
    data = data[data["intervention_class"].isin(["probiotic", "synbiotic"])].copy()
    data = data[_microbial_comparison_mask(data)].copy()
    data = data[_primary_study_title_mask(data)].copy()
    # A continuous effect-size regression needs a point estimate; the variance is
    # used for inverse-variance weighting where available and degrades to uniform
    # weight otherwise (precision-weighted regression -> OLS fallback).
    data = data[pd.to_numeric(data["estimate"], errors="coerce").notna()].copy()
    # Keep the raw physical scale (not SMD) but canonicalize the free-text unit
    # label so e.g. "kg/m2 BMI change" and "kg/m2 change" form one stratum.
    data["canonical_unit"] = data["effect_unit"].map(_canonical_unit)
    data = data[~data["canonical_unit"].isin(["mixed", "unspecified"])].copy()
    data["stratum"] = data["outcome_domain"].astype(str) + "|" + data["canonical_unit"].astype(str)

    # Primary model: curated (high-confidence) effects only.
    primary = data[data["confidence"].str.lower().eq("high")].copy()
    primary_predictions, models, primary_strata = _fit_strata(primary, minimum_studies)
    # Sensitivity: also include abstract-mined (low-confidence) rows. Metrics only.
    _, _, sensitivity_strata = _fit_strata(data, minimum_studies)

    modeled = sum(
        row.get("status") == "leave_one_study_out_internal_validation" for row in primary_strata
    )
    strata_beating_null = sum(bool(row.get("beats_null_baseline")) for row in primary_strata)
    prediction_table = (
        pd.concat(primary_predictions, ignore_index=True)
        if primary_predictions
        else pd.DataFrame(
            columns=["effect_id", "study_id", "stratum", "estimate", "predicted_effect", "residual"]
        )
    )
    predictions_output.parent.mkdir(parents=True, exist_ok=True)
    prediction_table.to_csv(predictions_output, index=False)
    metrics = {
        "model_level": "study_arm_continuous_effect_meta_regression",
        "confidence_policy": confidence_policy,
        "effect_rows_available": int(len(effects)),
        "modeling_rows_all_confidence": int(len(data)),
        "modeling_rows_high_confidence": int(len(primary)),
        "modeling_rows_high_confidence_after_outlier_filter": None,
        "validation_ready_rows_high_confidence": int(
            primary["validation_ready"].astype(str).str.lower().eq("true").sum()
        )
        if len(primary)
        else 0,
        "high_confidence_independent_studies": (
            int(primary["analysis_study_id"].nunique()) if len(primary) else 0
        ),
        "high_confidence_independent_studies_after_outlier_filter": None,
        "weighting_policy": (
            "fold-local inverse direct variance where sufficiently available; "
            "otherwise uniform"
        ),
        "modeled_strata": int(modeled),
        "strata_beating_null_baseline": int(strata_beating_null),
        "minimum_studies_per_stratum": minimum_studies,
        "strata": primary_strata,
        "sensitivity_including_abstract_mined": sensitivity_strata,
        "model_status": (
            "predictive_signal_above_null_internal_only"
            if strata_beating_null
            else "fitted_but_no_signal_above_null_baseline"
            if modeled
            else "insufficient_continuous_effect_data"
        ),
        "combination_ranking_enabled": False,
        "limitation": (
            "Endpoint-unit specific leave-one-study-out internal validation only. "
            "Requires external-study validation and predictive lift over the stratum "
            "mean before any combination-ranking use."
        ),
    }
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    model_output.parent.mkdir(parents=True, exist_ok=True)
    with model_output.open("wb") as handle:
        pickle.dump(models, handle)
    return ContinuousModelResult(metrics_output, predictions_output, model_output, int(modeled))


def _fit_strata(
    data: pd.DataFrame, minimum_studies: int
) -> tuple[list[pd.DataFrame], dict[str, object], list[dict[str, object]]]:
    """Leave-one-study-out inverse-variance ridge per outcome_domain|effect_unit stratum."""
    data = _add_interpretable_intervention_features(data)
    feature_columns = [
        "intervention_class",
        "microbial_family",
        "formulation_complexity",
        "dose_status",
        "duration_status",
        "dosage_form_group",
        "log10_cfu_per_day",
        "duration_weeks",
        "sample_size",
    ]
    predictions: list[pd.DataFrame] = []
    models: dict[str, object] = {}
    strata_metrics: list[dict[str, object]] = []
    if not len(data):
        return predictions, models, strata_metrics
    for stratum, raw_group in data.groupby("stratum"):
        study_column = (
            "analysis_study_id" if "analysis_study_id" in raw_group else "study_id"
        )
        group = _collapse_study_rows(raw_group, study_column)
        studies = group[study_column].nunique()
        if studies < minimum_studies or len(group) < minimum_studies:
            strata_metrics.append(
                {
                    "stratum": stratum,
                    "rows": int(len(group)),
                    "studies": int(studies),
                    "status": "insufficient_independent_studies",
                }
            )
            continue
        predictions_out = np.zeros(len(group), dtype=float)
        null_predictions = np.zeros(len(group), dtype=float)
        groups = group[study_column].astype(str).to_numpy()
        X = group[feature_columns]
        y = group["estimate"].astype(float).to_numpy()
        fold_weighting: list[str] = []
        fold_trimmed = 0
        for study in np.unique(groups):
            test = groups == study
            train = ~test
            train_group, trimmed = _trim_estimate_outliers(group.loc[train])
            if len(train_group) < max(3, minimum_studies - 1):
                train_group = group.loc[train]
                trimmed = 0
            fold_trimmed += trimmed
            train_weights, weighting = _training_weights(train_group)
            fold_weighting.append(weighting)
            model = _effect_pipeline()
            model.fit(
                train_group[feature_columns],
                train_group["estimate"].astype(float),
                ridge__sample_weight=train_weights,
            )
            predictions_out[test] = model.predict(X.loc[test])
            null_predictions[test] = np.average(
                train_group["estimate"].astype(float), weights=train_weights
            )
        final_group, final_trimmed = _trim_estimate_outliers(group)
        if len(final_group) < minimum_studies:
            final_group = group
            final_trimmed = 0
        final_weights, final_weighting = _training_weights(final_group)
        final_model = _effect_pipeline()
        final_model.fit(
            final_group[feature_columns],
            final_group["estimate"].astype(float),
            ridge__sample_weight=final_weights,
        )
        models[stratum] = final_model
        pred = group[["effect_id", "study_id", "stratum", "estimate"]].copy()
        pred["predicted_effect"] = predictions_out
        pred["null_predicted_effect"] = null_predictions
        pred["residual"] = pred["estimate"] - pred["predicted_effect"]
        predictions.append(pred)
        mae = float(mean_absolute_error(y, predictions_out))
        null_mae = float(mean_absolute_error(y, null_predictions))
        relative_improvement = (
            float((null_mae - mae) / null_mae) if null_mae > 0 else 0.0
        )
        direct_rows = int(
            group.get("variance_provenance", pd.Series(index=group.index, dtype=object))
            .isin(["reported_ci", "arm_sd_and_n"])
            .sum()
        )
        strata_metrics.append(
            {
                "stratum": stratum,
                "rows": int(len(group)),
                "studies": int(studies),
                "status": "leave_one_study_out_internal_validation",
                "rows_with_computed_variance": direct_rows,
                "outlier_rows_trimmed": int(final_trimmed),
                "training_fold_outlier_exclusions": int(fold_trimmed),
                "weighting": final_weighting,
                "fold_weighting": sorted(set(fold_weighting)),
                "mae": mae,
                "rmse": float(mean_squared_error(y, predictions_out) ** 0.5),
                "null_mae": null_mae,
                "weighted_null_mae": null_mae,
                "relative_mae_improvement": relative_improvement,
                "minimum_relative_improvement": 0.10,
                "beats_null_baseline": bool(relative_improvement >= 0.10),
            }
        )
    return predictions, models, strata_metrics


def _collapse_study_rows(group: pd.DataFrame, study_column: str) -> pd.DataFrame:
    rows: list[pd.Series] = []
    for _, study_rows in group.groupby(study_column, sort=False):
        direct = study_rows[
            study_rows.get(
                "variance_provenance", pd.Series(index=study_rows.index, dtype=object)
            ).isin(["reported_ci", "arm_sd_and_n"])
        ]
        if len(direct):
            rows.append(direct.sort_values("variance").iloc[0])
        else:
            row = study_rows.iloc[0].copy()
            row["estimate"] = float(study_rows["estimate"].astype(float).median())
            rows.append(row)
    return pd.DataFrame(rows).reset_index(drop=True)


def _training_weights(group: pd.DataFrame) -> tuple[np.ndarray, str]:
    variance = pd.to_numeric(group["variance"], errors="coerce").to_numpy(dtype=float)
    provenance = group.get(
        "variance_provenance", pd.Series(index=group.index, dtype=object)
    ).astype(str)
    direct = provenance.isin(["reported_ci", "arm_sd_and_n"]).to_numpy()
    has_var = np.isfinite(variance) & (variance > 0) & direct
    if int(has_var.sum()) >= 3 and int(has_var.sum()) >= 0.5 * len(group):
        fallback = float(np.median(variance[has_var]))
        completed = np.where(has_var, variance, fallback)
        return 1.0 / np.clip(completed, 1e-12, None), "inverse_direct_variance"
    return np.ones(len(group), dtype=float), "uniform_ols"


def _trim_estimate_outliers(group: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop implausible effect estimates (robust MAD filter).

    Curated extraction occasionally mis-reads an absolute endpoint or an unrelated
    number as a between-group change (e.g. a 202 kg "change"). These would dominate
    a least-squares fit, so they are trimmed and counted for re-curation follow-up.
    """
    y = pd.to_numeric(group["estimate"], errors="coerce")
    if y.notna().sum() < 4:
        return group, 0
    median = float(y.median())
    mad = float((y - median).abs().median())
    if mad > 1e-9:
        robust_z = 0.6745 * (y - median).abs() / mad
        keep = robust_z <= 3.5
    else:
        std = float(y.std(ddof=0))
        if std <= 1e-9:
            return group, 0
        keep = (y - median).abs() <= 5 * std
    keep = keep.fillna(False)
    trimmed = int((~keep).sum())
    return group[keep], trimmed


def _canonical_unit(value: object) -> str:
    """Normalize a free-text effect unit to a canonical physical-scale label.

    Preserves the raw measurement scale (kg, kg/m2, cm, ...) — this is unit-label
    harmonization, not effect-size standardization.
    """
    text = _text(value).lower().replace("^", "")
    if not text:
        return "unspecified"
    if "kg" in text and (
        "%" in text or "percent" in text or "percentage" in text or "relative" in text
    ):
        return "mixed"
    if "kg/m2" in text or "kg/m 2" in text:
        return "kg/m2"
    if "cm" in text:
        return "cm"
    if "mmol/l" in text:
        return "mmol/L"
    if "mmol/mol" in text:
        return "mmol/mol"
    if "mg/dl" in text:
        return "mg/dL"
    if "whr" in text or "waist-to-hip" in text:
        return "ratio"
    if "kg" in text:
        return "kg"
    if "%" in text or "percent" in text:
        return "%"
    return "unspecified"


def _effect_pipeline() -> Pipeline:
    numeric = ["log10_cfu_per_day", "duration_weeks", "sample_size"]
    categorical = [
        "intervention_class",
        "microbial_family",
        "formulation_complexity",
        "dose_status",
        "duration_status",
        "dosage_form_group",
    ]
    preprocess = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        (
                            "impute",
                            SimpleImputer(strategy="median", keep_empty_features=True),
                        ),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            ),
        ]
    )
    return Pipeline([("preprocess", preprocess), ("ridge", Ridge(alpha=10.0))])


def _add_interpretable_intervention_features(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    for column in ("species", "strain", "dosage_form"):
        if column not in data:
            data[column] = ""
    for column in ("log10_cfu_per_day", "duration_weeks"):
        if column not in data:
            data[column] = np.nan
    identity = (
        data["species"].fillna("").astype(str)
        + " "
        + data["strain"].fillna("").astype(str)
    ).str.lower()
    family = pd.Series("other_or_unknown", index=data.index, dtype=object)
    family[identity.str.contains(r"akkermansia|faecalibacter|bacteroides|parabacteroides|hafnia", regex=True)] = "next_generation"
    family[identity.str.contains(r"bifidobacter", regex=True)] = "bifidobacterium"
    family[identity.str.contains(r"lactobac|lacticaseibac|lactiplantibac|limosilactobac", regex=True)] = "lactobacillaceae"
    family[identity.str.contains(r"bacillus", regex=True)] = "bacillus"
    family[identity.str.contains(r";|,|\+|multi|mixture|consort", regex=True)] = "mixed_family"
    data["microbial_family"] = family
    data["formulation_complexity"] = np.where(
        identity.str.contains(r";|,|\+|multi|mixture|consort", regex=True),
        "multi_component",
        np.where(identity.str.strip().ne(""), "single_or_named", "unknown"),
    )
    data["dose_status"] = np.where(
        pd.to_numeric(data["log10_cfu_per_day"], errors="coerce").notna(),
        "known",
        "missing",
    )
    data["duration_status"] = np.where(
        pd.to_numeric(data["duration_weeks"], errors="coerce").notna(),
        "known",
        "missing",
    )
    dosage = data["dosage_form"].fillna("").astype(str).str.lower()
    data["dosage_form_group"] = np.select(
        [
            dosage.str.contains(r"capsule|tablet"),
            dosage.str.contains(r"powder|sachet"),
            dosage.str.contains(r"drink|beverage|yogurt|milk|food"),
        ],
        ["capsule_or_tablet", "powder_or_sachet", "food_or_beverage"],
        default="unknown_or_other",
    )
    return data


def _load_reviews(paths: list[Path]) -> pd.DataFrame:
    tables = [pd.read_csv(path) for path in paths]
    if not tables:
        raise ValueError("At least one outcome review path is required")
    return pd.concat(tables, ignore_index=True, sort=False).drop_duplicates(
        ["evidence_id", "outcome_domain"], keep="last"
    )


def _load_interventions(paths: list[Path]) -> dict[str, dict[str, object]]:
    if not paths:
        return {}
    table = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True, sort=False)
    if "review_status" in table:
        table["_confirmed"] = table["review_status"].fillna("").str.lower().eq("extracted")
        table = table.sort_values("_confirmed")
    table = table.drop_duplicates("evidence_id", keep="last")
    return {str(row["evidence_id"]): row.to_dict() for _, row in table.iterrows()}


def _microbial_mask(data: pd.DataFrame) -> pd.Series:
    fields = [
        field
        for field in [
            "title",
            "suggested_text",
            "comparison",
            "second_pass_intervention_snippets",
            "pdf_intervention_terms",
        ]
        if field in data
    ]
    text = data[fields].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    return text.str.contains(
        # food-grade probiotics
        r"probiotic|synbiotic|postbiotic|paraprobiotic|bifidobacter|lactobac|"
        r"lacticaseibac|lactiplantibac|limosilactobac|pediococc|lactococc|"
        r"bacillus coagulans|enterococcus faecium|streptococcus thermophilus|"
        # human-derived gut microbes / next-generation probiotics
        r"akkermansia|faecalibacterium|bacteroides|parabacteroides|roseburia|"
        r"anaerobutyricum|anaerostipes|christensenella|blautia|dysosmobacter|"
        r"phascolarctobacterium|hafnia alvei|clostridium butyricum|"
        r"next[- ]generation probiotic|live biotherapeutic",
        regex=True,
    )


def _arm_labels(comparison: str, row: pd.Series) -> tuple[str, str]:
    normalized = comparison.replace(" versus ", "_vs_").replace(" vs ", "_vs_")
    if "_vs_" in normalized:
        left, right = normalized.split("_vs_", 1)
        return left.replace("_", " ").strip(), right.replace("_", " ").strip()
    title = _text(row.get("title"))
    active = "microbial intervention"
    for term in ("synbiotic", "probiotic", "postbiotic"):
        if term in title.lower():
            active = term
            break
    return active, "placebo or usual-care control"


NGP_GENERA = (
    "akkermansia", "faecalibacterium", "bacteroides", "parabacteroides",
    "roseburia", "anaerobutyricum", "anaerostipes", "christensenella",
    "blautia", "dysosmobacter", "phascolarctobacterium", "hafnia",
    "clostridium butyricum",
)


def _intervention_class(label: str) -> str:
    lower = label.lower()
    if "synbiotic" in lower:
        return "synbiotic"
    # human-derived next-generation probiotics count as a microbial intervention
    if any(genus in lower for genus in NGP_GENERA) or "next-generation probiotic" in lower:
        return "probiotic"
    if "probiotic" in lower or "microbial" in lower:
        return "probiotic"
    if "placebo" in lower:
        return "placebo"
    if "control" in lower or "usual" in lower:
        return "control"
    return "other"


_LIPID_MMOL_TO_MGDL = {"TC": 38.67, "LDL": 38.67, "HDL": 38.67, "TG": 88.57}


def _lipid_subtype(text: str) -> str | None:
    """Classify a lipid clause as TG / LDL / HDL / TC (None if unlabelled)."""
    t = text.lower()
    if "triglycer" in t or re.search(r"\btg\b", t):
        return "TG"
    if "ldl" in t:
        return "LDL"
    if "hdl" in t:
        return "HDL"
    if "total cholesterol" in t or re.search(r"\btc\b", t) or "cholesterol" in t:
        return "TC"
    return None


def _lipid_clause_difference(clause: str) -> float | None:
    """Between-group difference from a clause: 'A vs B' -> first(A)-first(B), else single value."""
    num = r"[-+]?\d+(?:\.\d+)?"
    norm = clause.replace("−", "-").replace("–", "-").replace("—", "-")
    if re.search(r"\bvs\.?\b", norm, flags=re.IGNORECASE):
        left, right = re.split(r"\bvs\.?\b", norm, maxsplit=1, flags=re.IGNORECASE)
        ln, rn = re.search(num, left), re.search(num, right)
        return float(ln.group()) - float(rn.group()) if ln and rn else None
    n = re.search(num, norm)
    return float(n.group()) if n else None


def _split_lipid_into_subtypes(source_value: str, effect_unit: str) -> list[tuple[str, float]]:
    """De-mash a lipid row into per-subtype (subtype, between-group diff in mg/dL).

    The pooled lipid stratum mixes TC/LDL/HDL/TG and mg/dL/mmol/L; this yields one
    physically comparable (mg/dL) point estimate per labelled lipid subtype.
    """
    row_is_mmol = "mmol" in effect_unit.lower()
    out: list[tuple[str, float]] = []
    seen: set[str] = set()
    for clause in re.split(r"[;]", source_value):
        subtype = _lipid_subtype(f"{clause} {effect_unit}")
        if subtype is None or subtype in seen:
            continue
        diff = _lipid_clause_difference(clause)
        if diff is None:
            continue
        is_mmol = row_is_mmol or "mmol" in clause.lower()
        diff_mgdl = diff * _LIPID_MMOL_TO_MGDL[subtype] if is_mmol else diff
        if abs(diff_mgdl) > 100:  # implausible between-group lipid change
            continue
        seen.add(subtype)
        out.append((subtype, round(diff_mgdl, 3)))
    return out


def _two_arm_endpoint_difference(text: str) -> float | None:
    """Intervention-minus-control mean from a 'mean +/- sd vs mean +/- sd' phrase.

    Used to repair 'endpoint' rows whose curated effect_difference was corrupted by
    a mean/SD column misalignment (e.g. control_sd - intervention_mean). Returns the
    between-arm endpoint difference from the first arm pair, ignoring the SDs.
    """
    number = r"[-+]?\d+(?:\.\d+)?"
    normalized = text.replace("−", "-").replace("–", "-").replace("—", "-")
    match = re.search(
        rf"(?:^|[;])[^;]*?({number})\s*(?:\+/-|±)\s*{number}\s+vs\.?\s+"
        rf"[^;]*?({number})\s*(?:\+/-|±)\s*{number}",
        normalized,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return float(match.group(1)) - float(match.group(2))


def _parse_continuous_effect(text: str, sample_size_text: str) -> dict[str, object] | None:
    normalized = (
        text.replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("鈭?", "-")
    )
    number = r"[-+]?\d+(?:\.\d+)?"
    ci_match = re.search(
        rf"95\s*%?\s*CI\s*[:=]?\s*({number})\s*(?:to|,|;)\s*({number})",
        normalized,
        flags=re.IGNORECASE,
    )
    if not ci_match:
        ci_match = re.search(
            rf"95\s*%?\s*CI\s*[:=]?\s*({number})\s+-\s+({number})",
            normalized,
            flags=re.IGNORECASE,
        )
    estimate_match = re.search(
        rf"(?:adjusted\s+(?:group\s+)?difference|between[- ]group\s+difference|"
        rf"mean\s+difference|difference)\s*[:=]?\s*({number})",
        normalized,
        flags=re.IGNORECASE,
    )
    if estimate_match and ci_match:
        estimate = float(estimate_match.group(1))
        lower, upper = sorted((float(ci_match.group(1)), float(ci_match.group(2))))
        return {
            "effect_measure": "adjusted_mean_difference",
            "estimate": estimate,
            "standard_error": (upper - lower) / (2 * 1.96),
            "ci_lower": lower,
            "ci_upper": upper,
            "extraction_method": "adjusted_difference_with_95ci",
        }

    arm_match = re.search(
        rf"(?:^|[;])[^;]*?({number})\s*(?:\+/-|±)\s*({number})\s+vs\.?\s+"
        rf"[^;]*?({number})\s*(?:\+/-|±)\s*({number})",
        normalized,
        flags=re.IGNORECASE,
    )
    if not arm_match:
        return None
    intervention_mean, intervention_sd, control_mean, control_sd = map(
        float, arm_match.groups()
    )
    sample_sizes = _arm_sample_sizes(sample_size_text)
    if sample_sizes is None:
        return {
            "effect_measure": "unadjusted_mean_difference",
            "estimate": intervention_mean - control_mean,
            "standard_error": None,
            "ci_lower": None,
            "ci_upper": None,
            "intervention_mean": intervention_mean,
            "intervention_sd": intervention_sd,
            "control_mean": control_mean,
            "control_sd": control_sd,
            "extraction_method": "two_arm_mean_sd_missing_arm_n",
        }
    intervention_n, control_n = sample_sizes
    se = (intervention_sd**2 / intervention_n + control_sd**2 / control_n) ** 0.5
    estimate = intervention_mean - control_mean
    return {
        "effect_measure": "unadjusted_mean_difference",
        "estimate": estimate,
        "standard_error": se,
        "ci_lower": estimate - 1.96 * se,
        "ci_upper": estimate + 1.96 * se,
        "intervention_mean": intervention_mean,
        "intervention_sd": intervention_sd,
        "intervention_n": intervention_n,
        "control_mean": control_mean,
        "control_sd": control_sd,
        "control_n": control_n,
        "extraction_method": "two_arm_mean_sd_and_arm_n",
    }


def _arm_sample_sizes(text: str) -> tuple[float, float] | None:
    per_arm = re.search(r"(\d+)\s+per\s+arm", text, flags=re.IGNORECASE)
    if per_arm:
        size = float(per_arm.group(1))
        return size, size
    sizes = [float(value) for value in re.findall(r"\bn\s*=\s*(\d+)", text, re.I)]
    if len(sizes) >= 2 and not re.search(r"randomized.*completed", text, re.I):
        return sizes[0], sizes[1]
    return None


def _sample_size(value: object) -> float | None:
    match = re.search(r"\bn\s*=\s*(\d+)", _text(value), flags=re.IGNORECASE)
    return float(match.group(1)) if match else _number(value)


def _duration_weeks(value: object) -> float | None:
    text = _text(value).lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(week|month|day)", text)
    if not match:
        return None
    amount = float(match.group(1))
    return amount * {"week": 1.0, "month": 4.345, "day": 1 / 7}[match.group(2)]


def _number(value: object) -> float | None:
    try:
        number = float(value)
        return number if np.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value).strip()
