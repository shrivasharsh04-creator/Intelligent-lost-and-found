"""
Section 10.1 -- Prototype Evaluation
--------------------------------------
Runs the match engine over a small, hand-labelled sample of lost/found
pairs (exact matches, partial matches, semantically-similar-but-differently
-worded matches, and unrelated pairs) and reports the evaluation
parameters called out in the synopsis:

  * Precision of high-confidence potential matches
  * False-positive rate for incorrectly suggested matches
  * Ranking quality (is the true match ranked #1 among candidates?)
  * Average response time for generating potential matches

Run:  python evaluate.py
"""

import time

from ai.matching_engine import compute_match, NOTIFICATION_THRESHOLD

UPLOAD_DIR = "uploads"  # unused here since the labelled set is text-only

# Each row: (lost_desc, lost_cat, lost_colour, lost_loc, lost_time,
#            found_desc, found_cat, found_colour, found_loc, found_time,
#            is_true_match)
LABELLED_PAIRS = [
    # True matches -- differently worded (Section 1 / 10.2 scenario)
    ("Black Lenovo laptop bag with a red logo, lost near Computer Lab 3.",
     "Bag / Backpack", "black", "Computer Lab 3", "2026-08-18T10:00",
     "Black laptop backpack found outside the computer laboratory with a Lenovo logo.",
     "Bag / Backpack", "black", "Computer Lab 2", "2026-08-18T12:00", True),

    ("Silver iPhone with a cracked screen, lost in the library reading hall.",
     "Electronics", "silver", "Library", "2026-08-15T09:00",
     "Found a silver mobile phone with a broken screen near the book bank.",
     "Electronics", "silver", "Library", "2026-08-15T09:45", True),

    ("Blue and white student identity card lost near the main gate.",
     "ID Card / Documents", "blue", "Main Gate", "2026-08-10T08:00",
     "A university ID card found near the security office at the entrance.",
     "ID Card / Documents", "blue", "Security Office", "2026-08-10T08:40", True),

    # True match -- same wording, exact match
    ("Brown leather wallet containing a college ID, lost near the canteen.",
     "Wallet / Purse", "brown", "Canteen", "2026-08-12T13:00",
     "Brown leather wallet containing a college ID, found near the canteen.",
     "Wallet / Purse", "brown", "Canteen", "2026-08-12T13:20", True),

    # Non-matches -- same category, unrelated items
    ("Black Lenovo laptop bag lost near Computer Lab 3.",
     "Bag / Backpack", "black", "Computer Lab 3", "2026-08-18T10:00",
     "Red gym bag found near the sports ground.",
     "Bag / Backpack", "red", "Sports Ground", "2026-08-01T10:00", False),

    ("Silver iPhone lost in the library.",
     "Electronics", "silver", "Library", "2026-08-15T09:00",
     "Black wired earphones found in lecture hall 1.",
     "Electronics", "black", "Lecture Hall 1", "2026-08-20T09:00", False),

    ("Blue student ID card lost near main gate.",
     "ID Card / Documents", "blue", "Main Gate", "2026-08-10T08:00",
     "Steel water bottle found in the library.",
     "Other", "silver", "Library", "2026-08-10T08:00", False),

    ("Brown leather wallet lost near the canteen.",
     "Wallet / Purse", "brown", "Canteen", "2026-08-12T13:00",
     "Set of keys with a red keychain found in hostel A.",
     "Keys", "red", "Hostel A", "2026-08-12T13:00", False),
]


REVIEW_THRESHOLD = 0.50  # Section 5.5 "possible match requiring manual review" floor


def _score_at_threshold(rows, threshold):
    tp = fp = fn = tn = 0
    for result, is_true in rows:
        predicted_positive = result["total_score"] >= threshold
        if predicted_positive and is_true:
            tp += 1
        elif predicted_positive and not is_true:
            fp += 1
        elif not predicted_positive and is_true:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else None
    fpr = fp / (fp + tn) if (fp + tn) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    return precision, fpr, recall


def _fmt(x):
    return f"{x:.2f}" if x is not None else "n/a (no predicted positives in this sample)"


def run():
    rows = []
    durations = []

    print("Note: this labelled sample is text/attribute-only (no photos), so image_score is\n"
          "always 0 here; a real deployment with photos scores meaningfully higher. See README.\n")
    print(f"{'#':<3}{'true?':<7}{'score':<8}{'category':<14}{'time(ms)':<10}")
    for i, row in enumerate(LABELLED_PAIRS, start=1):
        (ldesc, lcat, lcol, lloc, ltime,
         fdesc, fcat, fcol, floc, ftime, is_true) = row

        lost = {"item_id": i, "description": ldesc, "category": lcat, "colour": lcol,
                "location": lloc, "date_time": ltime, "image_reference": None}
        found = {"item_id": 100 + i, "description": fdesc, "category": fcat, "colour": fcol,
                 "location": floc, "date_time": ftime, "image_reference": None}

        start = time.perf_counter()
        result = compute_match(lost, found, UPLOAD_DIR)
        elapsed_ms = (time.perf_counter() - start) * 1000
        durations.append(elapsed_ms)
        rows.append((result, is_true))

        print(f"{i:<3}{str(is_true):<7}{result['total_score']:<8.3f}{result['match_category']:<14}{elapsed_ms:<10.2f}")

    notify_precision, notify_fpr, notify_recall = _score_at_threshold(rows, NOTIFICATION_THRESHOLD)
    review_precision, review_fpr, review_recall = _score_at_threshold(rows, REVIEW_THRESHOLD)
    avg_ms = sum(durations) / len(durations)

    print("\n--- Section 10.1 Evaluation Summary ---")
    print(f"[Auto-notify @ {NOTIFICATION_THRESHOLD*100:.0f}%] precision={_fmt(notify_precision)}  "
          f"false-positive-rate={_fmt(notify_fpr)}  recall={_fmt(notify_recall)}")
    print(f"[Manual-review floor @ {REVIEW_THRESHOLD*100:.0f}%] precision={_fmt(review_precision)}  "
          f"false-positive-rate={_fmt(review_fpr)}  recall={_fmt(review_recall)}")
    print(f"Average response time per match computation: {avg_ms:.2f} ms")


if __name__ == "__main__":
    run()
