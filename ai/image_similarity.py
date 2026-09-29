"""
Module 6 -- Image Similarity Engine
-------------------------------------
Provides visual similarity evidence between an uploaded lost-item photo
and an uploaded found-item photo (Section 5.3). Two classical,
dependency-light computer-vision signals are combined so the prototype
needs no internet access or pretrained deep-learning weights:

1. HSV colour-histogram correlation -- captures overall colour/appearance
   similarity (robust to minor rotation/scale changes).
2. ORB keypoint descriptor matching -- captures local structural/shape
   similarity (logos, edges, texture) using a brute-force Hamming matcher.

The two signals are averaged into a single 0..1 image_score. The
interface is intentionally isolated in this module so it can later be
swapped for a CNN embedding + cosine-similarity approach (e.g. a
pretrained ResNet/CLIP feature extractor) without changing callers.
"""

import cv2
import numpy as np

from ai.preprocessing import load_image_for_features

orb = cv2.ORB_create(nfeatures=500)
bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)


def _colour_histogram_score(img_a, img_b) -> float:
    hsv_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2HSV)
    hsv_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2HSV)

    hist_a = cv2.calcHist([hsv_a], [0, 1], None, [50, 60], [0, 180, 0, 256])
    hist_b = cv2.calcHist([hsv_b], [0, 1], None, [50, 60], [0, 180, 0, 256])
    cv2.normalize(hist_a, hist_a)
    cv2.normalize(hist_b, hist_b)

    corr = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
    # cv2 correlation is in [-1, 1]; rescale to [0, 1]
    return float(max(0.0, min(1.0, (corr + 1) / 2)))


def _orb_structural_score(img_a, img_b) -> float:
    gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)

    kp_a, des_a = orb.detectAndCompute(gray_a, None)
    kp_b, des_b = orb.detectAndCompute(gray_b, None)

    if des_a is None or des_b is None or len(kp_a) == 0 or len(kp_b) == 0:
        return 0.0

    matches = bf_matcher.match(des_a, des_b)
    if not matches:
        return 0.0

    good = [m for m in matches if m.distance < 60]
    denom = max(min(len(kp_a), len(kp_b)), 1)
    return float(max(0.0, min(1.0, len(good) / denom)))


def image_similarity(path_a: str, path_b: str) -> float:
    """Return a 0..1 visual similarity score between two image files on
    disk. Returns 0.0 if either image is missing/unreadable (image
    evidence is then simply excluded / down-weighted by the caller)."""
    if not path_a or not path_b:
        return 0.0

    img_a = load_image_for_features(path_a)
    img_b = load_image_for_features(path_b)
    if img_a is None or img_b is None:
        return 0.0

    colour_score = _colour_histogram_score(img_a, img_b)
    structural_score = _orb_structural_score(img_a, img_b)

    # colour is weighted slightly higher than structural matching because
    # phone-camera found-item photos are commonly taken from different
    # angles than the lost-item photo, which hurts ORB matching more than
    # it hurts overall colour appearance.
    return float(0.6 * colour_score + 0.4 * structural_score)
