import math
import re
from typing import Any


RISK_LEVELS: dict[str, tuple[float, float]] = {
    "LOW": (0.0, 25.0),
    "MEDIUM": (25.0, 50.0),
    "HIGH": (50.0, 75.0),
    "CRITICAL": (75.0, 100.0),
}

ESCALATION_LEXICON: dict[str, float] = {
    "war": 0.9, "attack": 0.85, "strike": 0.8, "invasion": 0.95,
    "threat": 0.7, "destroy": 0.85, "annihilate": 0.95, "retaliate": 0.75,
    "sanctions": 0.5, "embargo": 0.6, "blockade": 0.7, "mobilize": 0.65,
    "deploy": 0.55, "escalate": 0.8, "conflict": 0.65, "aggression": 0.75,
    "sovereignty": 0.4, "intervention": 0.6, "regime": 0.5, "collapse": 0.7,
    "crisis": 0.6, "emergency": 0.55, "nuclear": 0.95, "missile": 0.8,
    "military": 0.5, "combat": 0.75, "terror": 0.85, "extremist": 0.7,
    "insurgency": 0.7, "coup": 0.85, "overthrow": 0.8, "resistance": 0.45,
    "occupation": 0.7, "annex": 0.8, "seize": 0.65, "force": 0.5,
    "ultimatum": 0.75, "confrontation": 0.65, "hostile": 0.7, "defend": 0.4,
}

DEESCALATION_LEXICON: dict[str, float] = {
    "peace": 0.8, "negotiate": 0.7, "diplomacy": 0.65, "agreement": 0.75,
    "treaty": 0.8, "ceasefire": 0.85, "de-escalate": 0.8, "cooperation": 0.6,
    "dialogue": 0.6, "resolution": 0.7, "sanctions relief": 0.5,
    "normalization": 0.65, "accord": 0.75, "compromise": 0.6,
}

SIGNAL_WEIGHTS: dict[str, float] = {
    "arms_transfer": 0.30,
    "military_exercise": 0.20,
    "political_rhetoric": 0.25,
    "economic_stress": 0.15,
    "intelligence_alert": 0.10,
}


def moving_average(values: list[float], window: int = 3) -> list[float]:
    if not values or window <= 0:
        return []
    result: list[float] = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_slice = values[start:i + 1]
        result.append(sum(window_slice) / len(window_slice))
    return result


def standard_deviation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def z_score(value: float, mean: float, std: float) -> float:
    if std == 0:
        return 0.0
    return (value - mean) / std


def exponential_smoothing(values: list[float], alpha: float = 0.3) -> list[float]:
    if not values:
        return []
    smoothed: list[float] = [values[0]]
    for i in range(1, len(values)):
        smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[i - 1])
    return smoothed


def double_exponential_smoothing(
    values: list[float],
    alpha: float = 0.3,
    beta: float = 0.1,
) -> tuple[list[float], float]:
    if not values:
        return [], 0.0
    if len(values) == 1:
        return [values[0]], 0.0

    level: list[float] = [values[0]]
    trend: list[float] = [values[1] - values[0] if len(values) > 1 else 0.0]
    smoothed: list[float] = [values[0]]

    for i in range(1, len(values)):
        new_level = alpha * values[i] + (1 - alpha) * (level[-1] + trend[-1])
        new_trend = beta * (new_level - level[-1]) + (1 - beta) * trend[-1]
        level.append(new_level)
        trend.append(new_trend)
        smoothed.append(new_level + new_trend)

    return smoothed, trend[-1]


def forecast_trend(values: list[float], periods: int = 6) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [values[0]] * periods

    _, final_trend = double_exponential_smoothing(values)
    smoothed = exponential_smoothing(values)
    last_value = smoothed[-1]

    forecast: list[float] = []
    for p in range(1, periods + 1):
        forecast.append(last_value + final_trend * p)

    return forecast


def classify_risk_level(score: float) -> str:
    for level, (low, high) in RISK_LEVELS.items():
        if low <= score < high:
            return level
    return "CRITICAL"


def detect_escalation(texts: list[str]) -> dict[str, Any]:
    if not texts:
        return {
            "escalation_score": 0.0,
            "risk_level": "LOW",
            "confidence": 0.0,
            "signals": [],
            "dominant_themes": [],
        }

    escalation_hits: list[dict[str, Any]] = []
    deescalation_hits: list[dict[str, Any]] = []
    theme_counts: dict[str, int] = {}
    text_scores: list[float] = []

    for idx, text in enumerate(texts):
        lower_text = text.lower()
        words = re.findall(r"\b\w[\w-]*\w\b|\b\w+\b", lower_text)
        text_escalation: float = 0.0
        text_deescalation: float = 0.0

        for word in words:
            if word in ESCALATION_LEXICON:
                weight = ESCALATION_LEXICON[word]
                text_escalation += weight
                escalation_hits.append({
                    "text_index": idx,
                    "term": word,
                    "weight": weight,
                })
                theme_counts[word] = theme_counts.get(word, 0) + 1

            if word in DEESCALATION_LEXICON:
                weight = DEESCALATION_LEXICON[word]
                text_deescalation += weight
                deescalation_hits.append({
                    "text_index": idx,
                    "term": word,
                    "weight": weight,
                })

        intensity_modifiers = _count_intensity_modifiers(lower_text)
        text_escalation *= (1.0 + intensity_modifiers * 0.15)
        net_score = text_escalation - text_deescalation * 0.6
        text_scores.append(net_score)

    avg_score = sum(text_scores) / len(text_scores) if text_scores else 0.0
    max_score = max(text_scores) if text_scores else 0.0
    std = standard_deviation(text_scores) if len(text_scores) > 1 else 0.0

    composite = (avg_score * 0.6 + max_score * 0.4)
    normalized = min(100.0, max(0.0, composite * 12.0))

    total_hits = len(escalation_hits) + len(deescalation_hits)
    confidence = _compute_confidence(total_hits, len(texts), std)

    dominant_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "escalation_score": round(normalized, 2),
        "risk_level": classify_risk_level(normalized),
        "confidence": round(confidence, 2),
        "signals": escalation_hits[:20],
        "deescalation_signals": deescalation_hits[:10],
        "dominant_themes": [{"theme": t, "count": c} for t, c in dominant_themes],
        "text_count": len(texts),
        "mean_text_score": round(avg_score, 4),
        "max_text_score": round(max_score, 4),
    }


def _count_intensity_modifiers(text: str) -> int:
    intensifiers = [
        "immediately", "urgent", "critical", "severe", "extreme",
        "unprecedented", "massive", "total", "full-scale", "all-out",
        "without delay", "no choice", "must", "will not tolerate",
        "grave consequences", "final warning", "last resort",
    ]
    count = 0
    for modifier in intensifiers:
        if modifier in text:
            count += 1
    if text.count("!") > 1:
        count += 1
    if any(c.isupper() for c in text.split()):
        count += 1
    return count


def _compute_confidence(hit_count: int, text_count: int, std: float) -> float:
    if text_count == 0:
        return 0.0

    volume_factor = min(1.0, text_count / 10.0)
    hit_factor = min(1.0, hit_count / (text_count * 3.0))
    consistency_factor = 1.0 / (1.0 + std) if std > 0 else 0.5

    confidence = (volume_factor * 0.3 + hit_factor * 0.4 + consistency_factor * 0.3)
    return min(1.0, max(0.0, confidence))


def compute_risk_score(country_iso: str, signals: list[dict]) -> dict[str, Any]:
    if not signals:
        return {
            "country_iso": country_iso,
            "risk_score": 0.0,
            "risk_level": "LOW",
            "confidence": 0.0,
            "signal_breakdown": {},
            "trend": "STABLE",
            "anomalies": [],
        }

    categorized: dict[str, list[float]] = {}
    for signal in signals:
        sig_type = signal.get("type", "unknown")
        value = float(signal.get("value", 0.0))
        if sig_type not in categorized:
            categorized[sig_type] = []
        categorized[sig_type].append(value)

    signal_breakdown: dict[str, dict[str, Any]] = {}
    weighted_sum: float = 0.0
    total_weight: float = 0.0
    all_anomalies: list[dict[str, Any]] = []

    for sig_type, values in categorized.items():
        weight = SIGNAL_WEIGHTS.get(sig_type, 0.05)
        avg_value = sum(values) / len(values)
        std = standard_deviation(values) if len(values) > 1 else 0.0
        smoothed = exponential_smoothing(values)
        trend_direction = _determine_trend(smoothed)

        normalized = _normalize_signal(avg_value, sig_type)
        weighted_sum += normalized * weight
        total_weight += weight

        anomalies_in_type: list[dict[str, Any]] = []
        if std > 0:
            for i, v in enumerate(values):
                z = z_score(v, avg_value, std)
                if abs(z) > 2.0:
                    anomalies_in_type.append({
                        "type": sig_type,
                        "index": i,
                        "value": v,
                        "z_score": round(z, 3),
                    })

        all_anomalies.extend(anomalies_in_type)

        signal_breakdown[sig_type] = {
            "raw_average": round(avg_value, 4),
            "normalized": round(normalized, 2),
            "weight": weight,
            "weighted_contribution": round(normalized * weight, 4),
            "std": round(std, 4),
            "trend": trend_direction,
            "anomaly_count": len(anomalies_in_type),
            "data_points": len(values),
        }

    raw_score = (weighted_sum / total_weight * 100.0) if total_weight > 0 else 0.0

    anomaly_bonus = min(15.0, len(all_anomalies) * 3.0)
    adjusted_score = min(100.0, raw_score + anomaly_bonus)

    confidence = _compute_signal_confidence(signals, categorized)
    trend = _compute_overall_trend(signal_breakdown)

    return {
        "country_iso": country_iso,
        "risk_score": round(adjusted_score, 2),
        "risk_level": classify_risk_level(adjusted_score),
        "confidence": round(confidence, 2),
        "signal_breakdown": signal_breakdown,
        "trend": trend,
        "anomalies": all_anomalies,
        "total_signals": len(signals),
        "signal_types": list(categorized.keys()),
    }


def _normalize_signal(value: float, sig_type: str) -> float:
    ranges: dict[str, tuple[float, float]] = {
        "arms_transfer": (0.0, 1000.0),
        "military_exercise": (0.0, 50.0),
        "political_rhetoric": (0.0, 100.0),
        "economic_stress": (0.0, 100.0),
        "intelligence_alert": (0.0, 10.0),
    }
    low, high = ranges.get(sig_type, (0.0, 100.0))
    normalized = (value - low) / (high - low) if high > low else 0.0
    return min(1.0, max(0.0, normalized))


def _determine_trend(smoothed: list[float]) -> str:
    if len(smoothed) < 2:
        return "STABLE"
    first_half = smoothed[:len(smoothed) // 2]
    second_half = smoothed[len(smoothed) // 2:]
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    diff = avg_second - avg_first
    threshold = abs(avg_first) * 0.05 if avg_first != 0 else 0.01
    if diff > threshold:
        return "INCREASING"
    elif diff < -threshold:
        return "DECREASING"
    return "STABLE"


def _compute_overall_trend(breakdown: dict[str, dict[str, Any]]) -> str:
    if not breakdown:
        return "STABLE"
    increasing = sum(1 for s in breakdown.values() if s["trend"] == "INCREASING")
    decreasing = sum(1 for s in breakdown.values() if s["trend"] == "DECREASING")
    total = len(breakdown)
    if increasing > total * 0.5:
        return "INCREASING"
    elif decreasing > total * 0.5:
        return "DECREASING"
    return "STABLE"


def _compute_signal_confidence(
    signals: list[dict],
    categorized: dict[str, list[float]],
) -> float:
    type_coverage = len(categorized) / len(SIGNAL_WEIGHTS)
    data_sufficiency = min(1.0, len(signals) / 20.0)

    consistency_scores: list[float] = []
    for values in categorized.values():
        if len(values) >= 2:
            std = standard_deviation(values)
            mean = sum(values) / len(values)
            cv = std / mean if mean != 0 else 0.0
            consistency_scores.append(1.0 / (1.0 + cv))

    avg_consistency = (
        sum(consistency_scores) / len(consistency_scores)
        if consistency_scores
        else 0.5
    )

    confidence = type_coverage * 0.35 + data_sufficiency * 0.35 + avg_consistency * 0.30
    return min(1.0, max(0.0, confidence))
