"""
Module 7 -- Attribute Matching Engine
---------------------------------------
Calculates category, colour, location and time-proximity scores between
a lost-item report and a found-item report (Section 5.4).
"""

import math
from datetime import datetime
from difflib import SequenceMatcher

from ai.preprocessing import normalize_category, normalize_colour

# Campus areas grouped into clusters so that reports from nearby places
# (e.g. two labs on the same floor) still score partial location
# similarity even when the free-text location strings are not identical.
# This models "buildings/labs/library/hostels" from Section 6.2 for the
# MIT-WPU style target environment described in the synopsis.
LOCATION_CLUSTERS = [
    {"computer lab 1", "computer lab 2", "computer lab 3", "cs department", "server room"},
    {"library", "reading hall", "book bank"},
    {"canteen", "cafeteria", "food court"},
    {"main gate", "parking", "security office"},
    {"hostel a", "hostel b", "hostel c", "mess hall"},
    {"lecture hall 1", "lecture hall 2", "seminar hall", "auditorium"},
    {"sports ground", "gymnasium", "indoor stadium"},
]


def category_score(cat_a: str, cat_b: str) -> float:
    a, b = normalize_category(cat_a), normalize_category(cat_b)
    if not a or not b:
        return 0.0
    return 1.0 if a == b else 0.0


def colour_score(colour_a: str, colour_b: str) -> float:
    a, b = normalize_colour(colour_a), normalize_colour(colour_b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # partial credit for close string variants, e.g. "dark blue" vs "blue"
    ratio = SequenceMatcher(None, a, b).ratio()
    return round(ratio, 2) if ratio > 0.6 else 0.0


def location_score(loc_a: str, loc_b: str) -> float:
    if not loc_a or not loc_b:
        return 0.0
    a, b = loc_a.lower().strip(), loc_b.lower().strip()
    if a == b:
        return 1.0

    for cluster in LOCATION_CLUSTERS:
        if a in cluster and b in cluster:
            return 0.7

    ratio = SequenceMatcher(None, a, b).ratio()
    return round(ratio, 2) if ratio > 0.5 else 0.0


def time_proximity_score(datetime_a: str, datetime_b: str, half_life_hours: float = 48.0) -> float:
    """Exponential decay: identical timestamps score 1.0; the score
    halves every `half_life_hours` hours of difference (default 48h),
    modelling the idea that a found report filed the same day as a loss
    is much stronger evidence than one filed weeks later."""
    try:
        dt_a = datetime.fromisoformat(datetime_a)
        dt_b = datetime.fromisoformat(datetime_b)
    except (ValueError, TypeError):
        return 0.0

    hours_diff = abs((dt_a - dt_b).total_seconds()) / 3600.0
    score = math.exp(-0.6931 * hours_diff / half_life_hours)  # ln(2) decay
    return round(float(score), 3)
