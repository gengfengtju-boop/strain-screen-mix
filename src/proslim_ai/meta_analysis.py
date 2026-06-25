from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.stats import binomtest, chi2, norm, t as t_dist


def dersimonian_laird(estimates: np.ndarray, variances: np.ndarray) -> dict[str, object]:
    """Run a DerSimonian-Laird random-effects meta-analysis for one stratum."""
    y = np.asarray(estimates, dtype=float)
    v = np.asarray(variances, dtype=float)
    k = len(y)
    w = 1.0 / v
    theta_fe = float(np.sum(w * y) / np.sum(w))
    q = float(np.sum(w * (y - theta_fe) ** 2))
    df = k - 1
    c = float(np.sum(w) - np.sum(w**2) / np.sum(w))
    tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
    w_re = 1.0 / (v + tau2)
    theta = float(np.sum(w_re * y) / np.sum(w_re))
    se = float(np.sqrt(1.0 / np.sum(w_re)))
    ci_low, ci_high = theta - 1.96 * se, theta + 1.96 * se
    i2 = max(0.0, (q - df) / q) if q > 0 else 0.0
    q_p = float(1 - chi2.cdf(q, df)) if df > 0 else None
    if k >= 3:
        t_crit = float(t_dist.ppf(0.975, k - 2))
        pi_half = t_crit * float(np.sqrt(tau2 + se**2))
        pi_low, pi_high = theta - pi_half, theta + pi_half
    else:
        pi_low = pi_high = None
    return {
        "k_studies": k,
        "pooled_effect": round(theta, 4),
        "standard_error": round(se, 4),
        "ci95_low": round(ci_low, 4),
        "ci95_high": round(ci_high, 4),
        "ci_excludes_zero": bool(ci_low > 0 or ci_high < 0),
        "tau2": round(tau2, 4),
        "i2_percent": round(100 * i2, 1),
        "cochran_q": round(q, 4),
        "q_pvalue": round(q_p, 4) if q_p is not None else None,
        "prediction_interval_low": round(pi_low, 4) if pi_low is not None else None,
        "prediction_interval_high": round(pi_high, 4) if pi_high is not None else None,
    }


def paule_mandel_hartung_knapp(
    estimates: np.ndarray, variances: np.ndarray
) -> dict[str, object]:
    """Small-sample random-effects synthesis using PM tau2 and modified HKSJ.

    Paule-Mandel estimates between-study variance by solving Q(tau2)=k-1.
    Hartung-Knapp uses a t interval for the pooled effect. The variance safeguard
    prevents the HKSJ interval from becoming spuriously narrower than the
    conventional random-effects interval when only a few studies are available.
    """
    y = np.asarray(estimates, dtype=float)
    v = np.asarray(variances, dtype=float)
    if len(y) != len(v) or len(y) < 2:
        raise ValueError("Paule-Mandel HKSJ requires at least two paired effects")
    if not np.all(np.isfinite(y)) or not np.all(np.isfinite(v)) or np.any(v <= 0):
        raise ValueError("Effects and positive variances must be finite")

    k = len(y)
    df = k - 1

    def q_at(tau2: float) -> float:
        weights = 1.0 / (v + tau2)
        mean = float(np.sum(weights * y) / np.sum(weights))
        return float(np.sum(weights * (y - mean) ** 2))

    q_zero = q_at(0.0)
    if q_zero <= df:
        tau2 = 0.0
    else:
        upper = max(float(np.var(y, ddof=1)), float(np.max(v)), 1e-8)
        while q_at(upper) > df and upper < 1e12:
            upper *= 2.0
        tau2 = float(brentq(lambda value: q_at(value) - df, 0.0, upper))

    weights = 1.0 / (v + tau2)
    pooled = float(np.sum(weights * y) / np.sum(weights))
    q_re = q_at(tau2)
    conventional_se = float(np.sqrt(1.0 / np.sum(weights)))
    hksj_se = float(np.sqrt((q_re / df) / np.sum(weights)))
    adjusted_se = max(conventional_se, hksj_se)
    critical = float(t_dist.ppf(0.975, df))
    ci_low = pooled - critical * adjusted_se
    ci_high = pooled + critical * adjusted_se

    fixed_weights = 1.0 / v
    fixed_mean = float(np.sum(fixed_weights * y) / np.sum(fixed_weights))
    q_fixed = float(np.sum(fixed_weights * (y - fixed_mean) ** 2))
    i2 = max(0.0, (q_fixed - df) / q_fixed) if q_fixed > 0 else 0.0
    q_p = float(1 - chi2.cdf(q_fixed, df))

    if k >= 3:
        prediction_critical = float(t_dist.ppf(0.975, k - 2))
        prediction_half = prediction_critical * float(np.sqrt(tau2 + adjusted_se**2))
        prediction_low = pooled - prediction_half
        prediction_high = pooled + prediction_half
    else:
        prediction_low = prediction_high = None

    return {
        "k_studies": k,
        "pooled_effect": round(pooled, 4),
        "standard_error": round(adjusted_se, 4),
        "ci95_low": round(ci_low, 4),
        "ci95_high": round(ci_high, 4),
        "ci_excludes_zero": bool(ci_low > 0 or ci_high < 0),
        "tau2": round(tau2, 4),
        "i2_percent": round(100 * i2, 1),
        "cochran_q": round(q_fixed, 4),
        "q_pvalue": round(q_p, 4),
        "prediction_interval_low": (
            round(prediction_low, 4) if prediction_low is not None else None
        ),
        "prediction_interval_high": (
            round(prediction_high, 4) if prediction_high is not None else None
        ),
        "tau2_method": "Paule-Mandel",
        "interval_method": "modified Hartung-Knapp-Sidik-Jonkman",
        "hksj_variance_safeguard_applied": bool(hksj_se < conventional_se),
    }


def median_sign_sensitivity(
    estimates: np.ndarray,
    bootstrap_iterations: int = 10000,
    random_seed: int = 20260614,
) -> dict[str, object]:
    """Summarize study effects without requiring reported sampling variances.

    This is a sensitivity analysis, not a replacement for inverse-variance meta-analysis.
    The study-level median limits the influence of extreme estimates, while the exact sign
    test only asks whether effect directions are unusually unbalanced.
    """
    y = np.asarray(estimates, dtype=float)
    y = y[np.isfinite(y)]
    if len(y) < 2:
        raise ValueError("Median/sign sensitivity requires at least two finite effects")
    if bootstrap_iterations < 100:
        raise ValueError("bootstrap_iterations must be at least 100")

    rng = np.random.default_rng(random_seed)
    samples = rng.choice(y, size=(bootstrap_iterations, len(y)), replace=True)
    bootstrap_medians = np.median(samples, axis=1)
    ci_low, ci_high = np.quantile(bootstrap_medians, [0.025, 0.975])
    nonzero = y[y != 0]
    negative = int((nonzero < 0).sum())
    sign_p = (
        float(binomtest(negative, len(nonzero), p=0.5, alternative="two-sided").pvalue)
        if len(nonzero)
        else 1.0
    )
    full_median = float(np.median(y))
    loo_medians = np.array([np.median(np.delete(y, index)) for index in range(len(y))])
    target_sign = np.sign(full_median)
    loo_same_direction = (
        float(np.mean(np.sign(loo_medians) == target_sign)) if target_sign else 0.0
    )
    return {
        "k_studies": int(len(y)),
        "median_effect": round(full_median, 4),
        "bootstrap_ci95_low": round(float(ci_low), 4),
        "bootstrap_ci95_high": round(float(ci_high), 4),
        "bootstrap_probability_below_zero": round(float(np.mean(bootstrap_medians < 0)), 4),
        "negative_effect_studies": int((y < 0).sum()),
        "positive_effect_studies": int((y > 0).sum()),
        "zero_effect_studies": int((y == 0).sum()),
        "exact_sign_test_pvalue": round(sign_p, 4),
        "leave_one_study_out_direction_stability": round(loo_same_direction, 4),
    }


def missing_variance_sensitivity(
    estimates: np.ndarray,
    variances: np.ndarray,
    bootstrap_iterations: int = 10000,
    random_seed: int = 20260614,
) -> dict[str, object]:
    """Run transparent sensitivity scenarios when some study variances are absent."""
    y = np.asarray(estimates, dtype=float)
    v = np.asarray(variances, dtype=float)
    if len(y) != len(v) or len(y) < 2 or not np.all(np.isfinite(y)):
        raise ValueError("Paired finite effects and variances are required")

    observed = np.isfinite(v) & (v > 0)
    observed_values = v[observed]
    scenarios: dict[str, dict[str, object]] = {}
    if observed.sum() >= 2:
        scenarios["observed_variance_only"] = paule_mandel_hartung_knapp(
            y[observed], v[observed]
        )
    if observed.sum() >= 1:
        for name, fill_value in (
            ("impute_stratum_median_variance", float(np.median(observed_values))),
            ("impute_stratum_upper_quartile_variance", float(np.quantile(observed_values, 0.75))),
        ):
            completed = np.where(observed, v, fill_value)
            scenarios[name] = paule_mandel_hartung_knapp(y, completed)

    nonparametric = median_sign_sensitivity(
        y,
        bootstrap_iterations=bootstrap_iterations,
        random_seed=random_seed,
    )
    point_directions = {
        int(np.sign(result["pooled_effect"]))
        for result in scenarios.values()
        if result["pooled_effect"] != 0
    }
    median_direction = int(np.sign(nonparametric["median_effect"]))
    same_point_direction = len(point_directions) == 1 and (
        not point_directions or median_direction in point_directions
    )
    excluding_interval_directions = [
        -1 if result["ci95_high"] < 0 else 1
        for result in scenarios.values()
        if result["ci_excludes_zero"]
    ]
    interval_directions = set(excluding_interval_directions)
    median_ci_direction = (
        -1
        if nonparametric["bootstrap_ci95_high"] < 0
        else 1
        if nonparametric["bootstrap_ci95_low"] > 0
        else 0
    )
    if observed.sum() < 2:
        evidence_state = "sensitivity_only_insufficient_observed_variances"
    elif (
        len(interval_directions) == 1
        and len(excluding_interval_directions) == len(scenarios)
        and median_ci_direction in interval_directions
    ):
        evidence_state = "robust_direction_across_methods"
    elif same_point_direction and median_direction != 0:
        evidence_state = "directionally_consistent_but_uncertain"
    elif len(point_directions | ({median_direction} if median_direction else set())) > 1:
        evidence_state = "conflicting_directions"
    else:
        evidence_state = "inconclusive"

    return {
        "k_studies": int(len(y)),
        "observed_variance_studies": int(observed.sum()),
        "missing_variance_studies": int((~observed).sum()),
        "variance_scenarios": scenarios,
        "nonparametric_sensitivity": nonparametric,
        "evidence_state": evidence_state,
        "imputation_is_sensitivity_only": True,
    }


def leave_one_out_meta_influence(
    estimates: np.ndarray,
    variances: np.ndarray,
    labels: list[str] | np.ndarray,
) -> dict[str, object]:
    """Measure how much each study changes a PM/HKSJ pooled estimate."""
    y = np.asarray(estimates, dtype=float)
    v = np.asarray(variances, dtype=float)
    names = np.asarray(labels, dtype=object)
    if len(y) != len(v) or len(y) != len(names) or len(y) < 3:
        raise ValueError("At least three paired effects, variances, and labels are required")
    full = paule_mandel_hartung_knapp(y, v)
    full_direction = int(np.sign(full["pooled_effect"]))
    rows: list[dict[str, object]] = []
    for index, label in enumerate(names):
        retained = np.arange(len(y)) != index
        result = paule_mandel_hartung_knapp(y[retained], v[retained])
        shift = float(result["pooled_effect"] - full["pooled_effect"])
        rows.append(
            {
                "omitted_study": str(label),
                "pooled_effect": result["pooled_effect"],
                "ci95_low": result["ci95_low"],
                "ci95_high": result["ci95_high"],
                "absolute_pooled_shift": round(abs(shift), 4),
                "direction_flips": bool(
                    full_direction and int(np.sign(result["pooled_effect"])) != full_direction
                ),
                "ci_excludes_zero": result["ci_excludes_zero"],
            }
        )
    most_influential = max(rows, key=lambda row: row["absolute_pooled_shift"])
    return {
        "full_model": full,
        "leave_one_out": rows,
        "most_influential_study": most_influential["omitted_study"],
        "maximum_absolute_pooled_shift": most_influential["absolute_pooled_shift"],
        "any_direction_flip": any(row["direction_flips"] for row in rows),
        "any_leave_one_out_ci_excludes_zero": any(row["ci_excludes_zero"] for row in rows),
    }


def layered_evidence_sensitivity(
    estimates: np.ndarray,
    variances: np.ndarray,
    cointervention: np.ndarray,
    stronger_precision: np.ndarray,
    bootstrap_iterations: int = 5000,
    random_seed: int = 20260614,
) -> dict[str, object]:
    """Compare conclusions across progressively stricter evidence layers."""
    y = np.asarray(estimates, dtype=float)
    v = np.asarray(variances, dtype=float)
    co = np.asarray(cointervention, dtype=bool)
    strong = np.asarray(stronger_precision, dtype=bool)
    if not (len(y) == len(v) == len(co) == len(strong)) or len(y) < 2:
        raise ValueError("Layered sensitivity requires paired arrays with at least two rows")

    layer_masks = {
        "all_eligible": np.ones(len(y), dtype=bool),
        "exclude_flagged_cointerventions": ~co,
        "observed_variance_only": np.isfinite(v) & (v > 0),
        "stronger_precision_only": strong & np.isfinite(v) & (v > 0),
    }
    layers: dict[str, dict[str, object]] = {}
    for offset, (name, mask) in enumerate(layer_masks.items()):
        if int(mask.sum()) < 2:
            layers[name] = {"k_studies": int(mask.sum()), "status": "insufficient_studies"}
            continue
        layer = missing_variance_sensitivity(
            y[mask],
            v[mask],
            bootstrap_iterations=bootstrap_iterations,
            random_seed=random_seed + offset,
        )
        layer["status"] = "analyzed"
        layers[name] = layer

    analyzed = [layer for layer in layers.values() if layer.get("status") == "analyzed"]
    median_directions = {
        int(np.sign(layer["nonparametric_sensitivity"]["median_effect"]))
        for layer in analyzed
        if layer["nonparametric_sensitivity"]["median_effect"] != 0
    }
    interval_support = [
        (
            layer["nonparametric_sensitivity"]["bootstrap_ci95_high"] < 0
            or layer["nonparametric_sensitivity"]["bootstrap_ci95_low"] > 0
        )
        for layer in analyzed
    ]
    all_intervals_exclude_zero = bool(interval_support) and all(interval_support)
    if len(median_directions) > 1:
        conclusion = "direction_changes_across_evidence_layers"
    elif all_intervals_exclude_zero and len(analyzed) >= 3:
        conclusion = "stable_direction_with_interval_support"
    elif any(interval_support):
        conclusion = "interval_support_is_subset_dependent"
    elif len(median_directions) == 1:
        conclusion = "stable_direction_but_uncertain"
    else:
        conclusion = "inconclusive"
    return {
        "layers": layers,
        "analyzed_layers": len(analyzed),
        "conclusion": conclusion,
        "layers_with_interval_support": sum(interval_support),
        "imputation_remains_sensitivity_only": True,
    }


def meta_regression_moderator(
    estimates: np.ndarray, variances: np.ndarray, moderator: np.ndarray
) -> dict[str, object]:
    """Fit an exploratory fixed-effect meta-regression with one moderator."""
    y = np.asarray(estimates, float)
    v = np.asarray(variances, float)
    k = len(y)
    x = np.asarray(moderator, float)
    design = np.column_stack([np.ones(k), x])
    wmat = np.diag(1.0 / v)
    cov = np.linalg.inv(design.T @ wmat @ design)
    beta = cov @ (design.T @ wmat @ y)
    resid = y - design @ beta
    q_resid = float(resid @ wmat @ resid)
    df = k - 2
    resid_i2 = max(0.0, (q_resid - df) / q_resid) if q_resid > 0 else 0.0
    slope_se = float(np.sqrt(cov[1, 1]))
    z = float(beta[1] / slope_se) if slope_se > 0 else 0.0
    p = float(2 * (1 - norm.cdf(abs(z))))
    return {
        "k_studies": k,
        "intercept": round(float(beta[0]), 4),
        "moderator_slope": round(float(beta[1]), 4),
        "slope_se": round(slope_se, 4),
        "slope_p": round(p, 4),
        "residual_i2_percent": round(100 * resid_i2, 1),
        "moderator_varies": bool(np.ptp(x) > 0),
    }
