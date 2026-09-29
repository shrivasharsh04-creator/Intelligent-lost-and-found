"""
Module 4 -- Item Pre-processing
--------------------------------
Validates and normalizes textual fields, and prepares uploaded images
so that they are in a consistent form before similarity analysis
(Section 5.1 / 5.2 / 5.3 of the synopsis).
"""

import re
import string

import cv2
import numpy as np

# A small, hand-curated synonym table so that differently worded but
# semantically related item descriptions (Section 1's "laptop bag" vs
# "computer backpack" example) collapse onto shared vocabulary before
# the TF-IDF/cosine similarity stage in text_similarity.py.
SYNONYMS = {
    "bag": "backpack",
    "laptop bag": "backpack",
    "computer bag": "backpack",
    "rucksack": "backpack",
    "knapsack": "backpack",
    "mobile": "phone",
    "cellphone": "phone",
    "cell phone": "phone",
    "smartphone": "phone",
    "handset": "phone",
    "id card": "identity card",
    "idcard": "identity card",
    "college id": "identity card",
    "laptop": "computer",
    "notebook computer": "computer",
    "earphones": "headphones",
    "earbuds": "headphones",
    "headset": "headphones",
    "wallet": "purse",
    "specs": "spectacles",
    "glasses": "spectacles",
    "lab": "laboratory",
    "washroom": "restroom",
    "canteen": "cafeteria",
}

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "near", "outside",
    "inside", "on", "in", "at", "of", "with", "and", "or", "to", "for",
    "it", "this", "that", "found", "lost", "item", "object", "near",
    "around", "by", "has", "had", "have", "i", "my", "me", "please",
    "somewhere", "approximately", "about",
}


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, expand synonyms, drop stopwords."""
    if not text:
        return ""
    text = text.lower().strip()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text)

    # multi-word synonym expansion first (longest key first)
    for phrase in sorted(SYNONYMS, key=len, reverse=True):
        if phrase in text:
            text = text.replace(phrase, SYNONYMS[phrase])

    tokens = [t for t in text.split() if t not in STOPWORDS and len(t) > 1]
    return " ".join(tokens)


def normalize_colour(colour: str) -> str:
    if not colour:
        return ""
    c = colour.lower().strip()
    aliases = {
        "grey": "gray",
        "navy": "blue",
        "maroon": "red",
        "charcoal": "black",
        "jet black": "black",
        "off white": "white",
        "cream": "white",
        "golden": "yellow",
    }
    return aliases.get(c, c)


def normalize_category(category: str) -> str:
    if not category:
        return ""
    return category.lower().strip()


def load_image_for_features(path: str, size=(256, 256)):
    """Read an image from disk and resize/convert it for feature
    extraction. Returns a BGR numpy array or None if unreadable."""
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        return None
    img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    return img
