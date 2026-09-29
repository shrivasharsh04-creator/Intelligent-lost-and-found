"""
Seeds the database with demo users and a set of lost/found reports,
including the exact illustrative test scenario from Section 10.2 of the
synopsis, so the matching engine and UI can be exercised end-to-end
immediately after setup.

Run:  python seed_demo.py
"""

import os
from datetime import datetime, timedelta

import numpy as np
import cv2
from werkzeug.security import generate_password_hash

from db import get_db, init_db, DB_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")


def _make_synthetic_photo(path, base_colour_bgr, seed):
    """Generates a small synthetic 'product photo' (a coloured rectangle
    on a neutral background with a logo-like mark) so the image
    similarity module (Module 6) has real image bytes to compare without
    needing internet access to download stock photos. Two photos of the
    'same' item use the same seed-derived layout with slight jitter,
    mimicking two different phone-camera shots of one physical object.
    """
    rng = np.random.default_rng(seed)
    img = np.full((300, 300, 3), 235, dtype=np.uint8)  # light background
    jitter = rng.integers(-8, 8, size=3)
    colour = np.clip(np.array(base_colour_bgr) + jitter, 0, 255).tolist()

    x0, y0 = 60 + rng.integers(-5, 5), 70 + rng.integers(-5, 5)
    x1, y1 = 240 + rng.integers(-5, 5), 230 + rng.integers(-5, 5)
    cv2.rectangle(img, (x0, y0), (x1, y1), colour, thickness=-1)
    cv2.rectangle(img, (x0, y0), (x1, y1), (30, 30, 30), thickness=2)

    # a small "logo" square in the corner acts as an ORB-detectable feature
    cv2.rectangle(img, (x0 + 15, y0 + 15), (x0 + 45, y0 + 45), (0, 0, 200), -1)
    cv2.putText(img, "LOGO", (x0 + 10, y0 + 42), cv2.FONT_HERSHEY_SIMPLEX,
                0.35, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.imwrite(path, img)


def seed():
    init_db(reset=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    db = get_db()

    # -- Users -----------------------------------------------------------
    users = [
        ("Harsh Shrivas", "harsh@example.edu", "user", "password123"),
        ("Mihir Uikey", "mihir@example.edu", "user", "password123"),
        ("Ananya Rao", "ananya@example.edu", "user", "password123"),
        ("Admin User", "admin@example.edu", "admin", "admin123"),
    ]
    user_ids = {}
    for name, email, role, pw in users:
        cur = db.execute(
            "INSERT INTO users (name, email, role, password_hash) VALUES (?, ?, ?, ?)",
            (name, email, role, generate_password_hash(pw)),
        )
        user_ids[email] = cur.lastrowid

    now = datetime.utcnow()

    # -- Section 10.2 illustrative scenario: laptop bag / backpack -------
    lost_photo = os.path.join(UPLOAD_DIR, "demo_lost_bag.jpg")
    found_photo = os.path.join(UPLOAD_DIR, "demo_found_bag.jpg")
    _make_synthetic_photo(lost_photo, (30, 30, 30), seed=1)     # black bag, seed 1
    _make_synthetic_photo(found_photo, (35, 33, 28), seed=1)    # near-identical, seed 1 + jitter

    db.execute(
        """INSERT INTO items (report_type, category, title, description, colour, location,
                               date_time, image_reference, status, user_id)
           VALUES ('lost', 'Bag / Backpack', 'Black Lenovo laptop bag',
                   'Black Lenovo laptop bag with a red logo, lost near Computer Lab 3 on 18 August.',
                   'black', 'Computer Lab 3', ?, ?, 'open', ?)""",
        ((now - timedelta(hours=2)).isoformat(timespec="minutes"), "demo_lost_bag.jpg", user_ids["harsh@example.edu"]),
    )
    db.execute(
        """INSERT INTO items (report_type, category, title, description, colour, location,
                               date_time, image_reference, status, user_id)
           VALUES ('found', 'Bag / Backpack', 'Black backpack found outside CS lab',
                   'Black laptop backpack found outside the computer laboratory with a Lenovo logo.',
                   'black', 'Computer Lab 2', ?, ?, 'open', ?)""",
        (now.isoformat(timespec="minutes"), "demo_found_bag.jpg", user_ids["mihir@example.edu"]),
    )

    # -- Additional unrelated / distractor reports ------------------------
    wallet_photo = os.path.join(UPLOAD_DIR, "demo_lost_wallet.jpg")
    _make_synthetic_photo(wallet_photo, (90, 40, 140), seed=5)
    db.execute(
        """INSERT INTO items (report_type, category, title, description, colour, location,
                               date_time, image_reference, status, user_id)
           VALUES ('lost', 'Wallet / Purse', 'Brown leather wallet',
                   'Brown leather wallet with college ID card inside, lost near the canteen.',
                   'brown', 'Canteen', ?, ?, 'open', ?)""",
        ((now - timedelta(days=1)).isoformat(timespec="minutes"), "demo_lost_wallet.jpg", user_ids["ananya@example.edu"]),
    )

    bottle_photo = os.path.join(UPLOAD_DIR, "demo_found_bottle.jpg")
    _make_synthetic_photo(bottle_photo, (150, 150, 150), seed=9)
    db.execute(
        """INSERT INTO items (report_type, category, title, description, colour, location,
                               date_time, image_reference, status, user_id)
           VALUES ('found', 'Other', 'Steel water bottle',
                   'Plain steel water bottle found in the library reading hall.',
                   'silver', 'Library', ?, ?, 'open', ?)""",
        ((now - timedelta(hours=5)).isoformat(timespec="minutes"), "demo_found_bottle.jpg", user_ids["ananya@example.edu"]),
    )

    id_card_lost = None
    db.execute(
        """INSERT INTO items (report_type, category, title, description, colour, location,
                               date_time, status, user_id)
           VALUES ('lost', 'ID Card / Documents', 'MIT-WPU student ID card',
                   'Blue and white student identity card, name partially visible, lost near main gate.',
                   'blue', 'Main Gate', ?, 'open', ?)""",
        ((now - timedelta(hours=10)).isoformat(timespec="minutes"), user_ids["mihir@example.edu"]),
    )
    db.execute(
        """INSERT INTO items (report_type, category, title, description, colour, location,
                               date_time, status, user_id)
           VALUES ('found', 'ID Card / Documents', 'Student identity card found',
                   'A university identity card found near the security office at the entrance.',
                   'blue', 'Security Office', ?, 'open', ?)""",
        ((now - timedelta(hours=9)).isoformat(timespec="minutes"), user_ids["ananya@example.edu"]),
    )

    db.commit()
    db.close()
    print(f"Seed data loaded into {DB_PATH}")
    print("Demo logins:")
    print("  harsh@example.edu / password123")
    print("  mihir@example.edu / password123")
    print("  ananya@example.edu / password123")
    print("  admin@example.edu / admin123  (administrator)")


if __name__ == "__main__":
    seed()
