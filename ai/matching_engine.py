"""
Module 8 -- Intelligent Match Engine
---------------------------------------
Combines the text, image and attribute signals into a single configurable
match score, classifies it, and produces an explainable result
(Sections 5.4, 5.5, 5.6 of the synopsis).

    Match Score = 30% Text Similarity + 30% Image Similarity
                + 15% Location Similarity + 10% Category Match
                +  5% Colour Match       + 10% Time Proximity
"""

import os

from ai.text_similarity import text_similarity
from ai.image_similarity import image_similarity
from ai.attribute_scoring import (
    category_score,
    colour_score,
    location_score,
    time_proximity_score,
)

# Default configurable weights (Section 5.4). Kept as module-level so an
# admin-tunable settings screen could update them after evaluating the
# prototype dataset, per the synopsis's "weights are configurable" note.
DEFAULT_WEIGHTS = {
    "text": 0.30,
    "image": 0.30,
    "location": 0.15,
    "category": 0.10,
    "colour": 0.05,
    "time": 0.10,
}

NOTIFICATION_THRESHOLD = 0.75  # Section 3: "exceeds a configurable confidence threshold"


def classify_score(total_score: float) -> str:
    """Section 5.5 match classification bands."""
    pct = total_score * 100
    if pct >= 90:
        return "very_strong"
    if pct >= 75:
        return "strong"
    if pct >= 50:
        return "possible"
    return "low"


CLASSIFICATION_LABELS = {
    "very_strong": "Very strong potential match",
    "strong": "Strong potential match",
    "possible": "Possible match requiring manual review",
    "low": "Low-priority potential match",
}


def _explain(scores: dict, weights: dict) -> list:
    """Section 5.6 -- human-readable reasons behind the ranking."""
    reasons = []
    if scores["category"] >= 1.0:
        reasons.append("Category matched")
    if scores["text"] >= 0.6:
        reasons.append("Descriptions are semantically similar")
    elif scores["text"] >= 0.3:
        reasons.append("Descriptions share some related wording")
    if scores["location"] >= 0.9:
        reasons.append("Locations are the same")
    elif scores["location"] >= 0.6:
        reasons.append("Locations are nearby")
    if scores["image"] >= 0.6:
        reasons.append("Images have similar visual features")
    if scores["colour"] >= 0.9:
        reasons.append("Colours match")
    if scores["time"] >= 0.7:
        reasons.append("Reported dates are close")
    if not reasons:
        reasons.append("Only weak overlap found across available evidence")
    return reasons


def compute_match(lost_item: dict, found_item: dict, upload_dir: str,
                   weights: dict | None = None) -> dict:
    """Compute the full multi-factor match result between one lost
    report and one found report (both passed in as sqlite3.Row-like
    dicts from the `items` table)."""
    weights = weights or DEFAULT_WEIGHTS

    text_s = text_similarity(lost_item["description"], found_item["description"])

    img_path_a = (os.path.join(upload_dir, lost_item["image_reference"])
                  if lost_item["image_reference"] else None)
    img_path_b = (os.path.join(upload_dir, found_item["image_reference"])
                  if found_item["image_reference"] else None)
    image_s = image_similarity(img_path_a, img_path_b) if img_path_a and img_path_b else 0.0

    location_s = location_score(lost_item["location"], found_item["location"])
    category_s = category_score(lost_item["category"], found_item["category"])
    colour_s = colour_score(lost_item["colour"], found_item["colour"])
    time_s = time_proximity_score(lost_item["date_time"], found_item["date_time"])

    scores = {
        "text": text_s,
        "image": image_s,
        "location": location_s,
        "category": category_s,
        "colour": colour_s,
        "time": time_s,
    }

    total = sum(scores[k] * weights[k] for k in weights)
    total = round(min(1.0, max(0.0, total)), 4)

    category_label = classify_score(total)

    return {
        "lost_item_id": lost_item["item_id"],
        "found_item_id": found_item["item_id"],
        "text_score": round(text_s, 4),
        "image_score": round(image_s, 4),
        "location_score": round(location_s, 4),
        "category_score": round(category_s, 4),
        "colour_score": round(colour_s, 4),
        "time_score": round(time_s, 4),
        "total_score": total,
        "match_category": category_label,
        "match_label": CLASSIFICATION_LABELS[category_label],
        "explanation": _explain(scores, weights),
        "should_notify": total >= NOTIFICATION_THRESHOLD,
    }


def rank_candidates(new_item: dict, candidates: list, upload_dir: str,
                     weights: dict | None = None, min_score: float = 0.0) -> list:
    """Compute + sort match results for a new report against every
    candidate report of the opposite type. Returns highest score first."""
    results = []
    for candidate in candidates:
        if new_item["report_type"] == "lost":
            result = compute_match(new_item, candidate, upload_dir, weights)
        else:
            result = compute_match(candidate, new_item, upload_dir, weights)
        if result["total_score"] >= min_score:
            results.append(result)
    results.sort(key=lambda r: r["total_score"], reverse=True)
    return results
