"""
Application / API Layer
------------------------
Flask REST + server-rendered routes tying the Presentation layer
(templates/) to the AI Processing layer (ai/) and Data layer (db.py),
exactly as described in Section 8 (System Architecture) of the
synopsis.

Run:
    python db.py            # one-time schema init
    python seed_demo.py     # optional: loads the illustrative test
                             # scenario from Section 10.2 + sample data
    python app.py           # starts the dev server on :5000
"""

import json
import os
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                    session, flash, jsonify, send_from_directory, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from db import get_db, init_db, DB_PATH
from ai.matching_engine import rank_candidates, compute_match, DEFAULT_WEIGHTS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB uploads

CATEGORIES = [
    "Electronics", "ID Card / Documents", "Bag / Backpack", "Wallet / Purse",
    "Keys", "Clothing / Accessories", "Books / Stationery", "Jewellery",
    "Sports Equipment", "Other",
]


# ----------------------------------------------------------------- utils
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Administrator access required.", "danger")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if "user_id" not in session:
        return None
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE user_id = ?", (session["user_id"],)).fetchone()
    db.close()
    return user


@app.context_processor
def inject_globals():
    unread = 0
    if "user_id" in session:
        db = get_db()
        unread = db.execute(
            "SELECT COUNT(*) c FROM notifications WHERE user_id = ? AND read_status = 0",
            (session["user_id"],),
        ).fetchone()["c"]
        db.close()
    return {"session": session, "unread_count": unread}


# ------------------------------------------------------------- Module 1
# User Authentication and Role Management
# -------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = "admin" if request.form.get("admin_signup") == "on" else "user"

        if not name or not email or len(password) < 6:
            flash("Please provide a valid name, email and a password of at least 6 characters.", "danger")
            return render_template("register.html")

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (name, email, role, password_hash) VALUES (?, ?, ?, ?)",
                (name, email, role, generate_password_hash(password)),
            )
            db.commit()
        except Exception:
            flash("That email is already registered.", "danger")
            return render_template("register.html")
        finally:
            db.close()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        db.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["user_id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("index"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ------------------------------------------------------------- Home
@app.route("/")
@login_required
def index():
    db = get_db()
    my_items = db.execute(
        "SELECT * FROM items WHERE user_id = ? ORDER BY created_at DESC", (session["user_id"],)
    ).fetchall()
    notifications = db.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
        (session["user_id"],),
    ).fetchall()
    stats = {
        "lost_open": db.execute("SELECT COUNT(*) c FROM items WHERE report_type='lost' AND status='open'").fetchone()["c"],
        "found_open": db.execute("SELECT COUNT(*) c FROM items WHERE report_type='found' AND status='open'").fetchone()["c"],
        "recovered": db.execute("SELECT COUNT(*) c FROM items WHERE status='recovered'").fetchone()["c"],
    }
    db.close()
    return render_template("index.html", my_items=my_items, notifications=notifications, stats=stats)


# ------------------------------------------------------------- Module 2 & 3
# Lost Item Management / Found Item Management
# -------------------------------------------------------------
def _handle_report(report_type):
    if request.method == "POST":
        category = request.form["category"].strip()
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        colour = request.form.get("colour", "").strip()
        location = request.form["location"].strip()
        date_time = request.form["date_time"].strip()
        unique_id = request.form.get("unique_id", "").strip()

        if not (category and title and description and location and date_time):
            flash("Please fill in all required fields.", "danger")
            return redirect(request.url)

        try:
            datetime.fromisoformat(date_time)
        except ValueError:
            flash("Date/time must be a valid ISO datetime (e.g. from the picker).", "danger")
            return redirect(request.url)

        image_filename = None
        file = request.files.get("image")
        if file and file.filename and allowed_file(file.filename):
            image_filename = f"{report_type}_{session['user_id']}_{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            file.save(os.path.join(UPLOAD_DIR, image_filename))

        db = get_db()
        cur = db.execute(
            """INSERT INTO items (report_type, category, title, description, colour,
                                   location, date_time, unique_id, image_reference, status, user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)""",
            (report_type, category, title, description, colour, location, date_time,
             unique_id, image_filename, session["user_id"]),
        )
        item_id = cur.lastrowid
        db.commit()
        db.close()

        flash(f"{report_type.capitalize()} item reported successfully.", "success")
        return redirect(url_for("view_matches", item_id=item_id))

    return render_template("report_item.html", report_type=report_type, categories=CATEGORIES)


@app.route("/report/lost", methods=["GET", "POST"])
@login_required
def report_lost():
    return _handle_report("lost")


@app.route("/report/found", methods=["GET", "POST"])
@login_required
def report_found():
    return _handle_report("found")


@app.route("/items")
@login_required
def list_items():
    report_type = request.args.get("type", "lost")
    q = request.args.get("q", "").strip()
    db = get_db()
    query = "SELECT * FROM items WHERE report_type = ? AND status != 'closed'"
    params = [report_type]
    if q:
        query += " AND (title LIKE ? OR description LIKE ? OR location LIKE ?)"
        like = f"%{q}%"
        params += [like, like, like]
    query += " ORDER BY created_at DESC"
    items = db.execute(query, params).fetchall()
    db.close()
    return render_template("list_items.html", items=items, report_type=report_type, q=q)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ------------------------------------------------------------- Modules 5-8
# AI Processing Layer entry point: Generate Potential Matches
# -------------------------------------------------------------
@app.route("/matches/<int:item_id>")
@login_required
def view_matches(item_id):
    db = get_db()
    item = db.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
    if item is None:
        db.close()
        abort(404)

    opposite_type = "found" if item["report_type"] == "lost" else "lost"
    candidates = db.execute(
        "SELECT * FROM items WHERE report_type = ? AND status = 'open'", (opposite_type,)
    ).fetchall()

    results = rank_candidates(dict(item), [dict(c) for c in candidates], UPLOAD_DIR, min_score=0.15)

    # persist / refresh match rows + fire notifications for strong matches
    candidate_by_id = {c["item_id"]: c for c in candidates}
    for r in results:
        counterpart_id = r["found_item_id"] if item["report_type"] == "lost" else r["lost_item_id"]
        existing = db.execute(
            "SELECT * FROM matches WHERE lost_item_id = ? AND found_item_id = ?",
            (r["lost_item_id"], r["found_item_id"]),
        ).fetchone()
        if existing is None:
            cur = db.execute(
                """INSERT INTO matches (lost_item_id, found_item_id, text_score, image_score,
                        location_score, category_score, colour_score, time_score,
                        total_score, match_category, explanation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (r["lost_item_id"], r["found_item_id"], r["text_score"], r["image_score"],
                 r["location_score"], r["category_score"], r["colour_score"], r["time_score"],
                 r["total_score"], r["match_category"], json.dumps(r["explanation"])),
            )
            match_id = cur.lastrowid
            if r["should_notify"]:
                counterpart = candidate_by_id[counterpart_id]
                _notify(db, counterpart["user_id"], match_id,
                        f"A {r['match_label'].lower()} ({int(r['total_score']*100)}%) was found for your "
                        f"{item['report_type']} report '{item['title']}'.")
                _notify(db, item["user_id"], match_id,
                        f"A {r['match_label'].lower()} ({int(r['total_score']*100)}%) was found for your "
                        f"{item['report_type']} report '{item['title']}'.")
        else:
            match_id = existing["match_id"]
        r["match_id"] = match_id
    db.commit()
    db.close()

    return render_template("matches.html", item=item, results=results,
                            candidate_by_id=candidate_by_id, weights=DEFAULT_WEIGHTS)


def _notify(db, user_id, match_id, message):
    db.execute(
        "INSERT INTO notifications (user_id, match_id, message) VALUES (?, ?, ?)",
        (user_id, match_id, message),
    )


@app.route("/notifications/read/<int:notification_id>", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    db = get_db()
    db.execute(
        "UPDATE notifications SET read_status = 1 WHERE notification_id = ? AND user_id = ?",
        (notification_id, session["user_id"]),
    )
    db.commit()
    db.close()
    return redirect(request.referrer or url_for("index"))


# ------------------------------------------------------------- Module 10
# Claim and Verification
# -------------------------------------------------------------
@app.route("/claim/<int:match_id>", methods=["GET", "POST"])
@login_required
def submit_claim(match_id):
    db = get_db()
    match = db.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,)).fetchone()
    if match is None:
        db.close()
        abort(404)
    lost_item = db.execute("SELECT * FROM items WHERE item_id = ?", (match["lost_item_id"],)).fetchone()
    found_item = db.execute("SELECT * FROM items WHERE item_id = ?", (match["found_item_id"],)).fetchone()

    if request.method == "POST":
        details = request.form["verification_details"].strip()
        if not details:
            flash("Please describe a non-public identifying detail (marks, stickers, contents, serial no.).", "danger")
        else:
            db.execute(
                """INSERT INTO claims (match_id, claimant_id, verification_details, status)
                   VALUES (?, ?, ?, 'pending')""",
                (match_id, session["user_id"], details),
            )
            db.execute("UPDATE items SET status = 'matched' WHERE item_id IN (?, ?)",
                       (match["lost_item_id"], match["found_item_id"]))
            db.commit()
            flash("Claim submitted. An administrator will review it shortly.", "success")
            db.close()
            return redirect(url_for("my_claims"))

    db.close()
    return render_template("claim_form.html", match=match, lost_item=lost_item, found_item=found_item)


@app.route("/my-claims")
@login_required
def my_claims():
    db = get_db()
    claims = db.execute(
        """SELECT c.*, m.total_score, m.match_category, li.title AS lost_title, fi.title AS found_title
           FROM claims c
           JOIN matches m ON m.match_id = c.match_id
           JOIN items li ON li.item_id = m.lost_item_id
           JOIN items fi ON fi.item_id = m.found_item_id
           WHERE c.claimant_id = ? ORDER BY c.created_at DESC""",
        (session["user_id"],),
    ).fetchall()
    db.close()
    return render_template("my_claims.html", claims=claims)


# ------------------------------------------------------------- Module 11
# Administration and Analytics
# -------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    total_users = db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    total_items = db.execute("SELECT COUNT(*) c FROM items").fetchone()["c"]
    total_matches = db.execute("SELECT COUNT(*) c FROM matches").fetchone()["c"]
    recovered = db.execute("SELECT COUNT(*) c FROM items WHERE status='recovered'").fetchone()["c"]
    pending_claims = db.execute("SELECT COUNT(*) c FROM claims WHERE status='pending'").fetchone()["c"]

    by_category = db.execute(
        "SELECT category, COUNT(*) c FROM items GROUP BY category ORDER BY c DESC"
    ).fetchall()
    by_location = db.execute(
        "SELECT location, COUNT(*) c FROM items GROUP BY location ORDER BY c DESC LIMIT 10"
    ).fetchall()
    claims = db.execute(
        """SELECT c.*, m.total_score, m.match_category, u.name AS claimant_name,
                  li.title AS lost_title, fi.title AS found_title
           FROM claims c
           JOIN matches m ON m.match_id = c.match_id
           JOIN users u ON u.user_id = c.claimant_id
           JOIN items li ON li.item_id = m.lost_item_id
           JOIN items fi ON fi.item_id = m.found_item_id
           ORDER BY c.created_at DESC"""
    ).fetchall()
    db.close()

    return render_template("admin_dashboard.html", total_users=total_users, total_items=total_items,
                            total_matches=total_matches, recovered=recovered,
                            pending_claims=pending_claims, by_category=by_category,
                            by_location=by_location, claims=claims)


@app.route("/admin/claims/<int:claim_id>/<action>", methods=["POST"])
@admin_required
def review_claim(claim_id, action):
    if action not in ("verify", "reject", "needs_info"):
        abort(400)
    status_map = {"verify": "verified", "reject": "rejected", "needs_info": "needs_info"}

    db = get_db()
    claim = db.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
    if claim is None:
        db.close()
        abort(404)

    db.execute(
        "UPDATE claims SET status = ?, reviewed_by = ?, reviewed_at = ? WHERE claim_id = ?",
        (status_map[action], session["user_id"], datetime.utcnow().isoformat(), claim_id),
    )

    if action == "verify":
        match = db.execute("SELECT * FROM matches WHERE match_id = ?", (claim["match_id"],)).fetchone()
        db.execute("UPDATE items SET status = 'recovered' WHERE item_id IN (?, ?)",
                   (match["lost_item_id"], match["found_item_id"]))
        _notify(db, claim["claimant_id"], claim["match_id"],
                "Your claim was verified. The item has been marked as recovered.")
    elif action == "reject":
        _notify(db, claim["claimant_id"], claim["match_id"],
                "Your claim was rejected by the administrator.")
        db.execute("UPDATE items SET status = 'open' WHERE item_id IN "
                   "(SELECT lost_item_id FROM matches WHERE match_id = ?)", (claim["match_id"],))
        db.execute("UPDATE items SET status = 'open' WHERE item_id IN "
                   "(SELECT found_item_id FROM matches WHERE match_id = ?)", (claim["match_id"],))
    else:
        _notify(db, claim["claimant_id"], claim["match_id"],
                "The administrator requested additional verification details for your claim.")

    db.commit()
    db.close()
    flash("Claim updated.", "success")
    return redirect(url_for("admin_dashboard"))


# ------------------------------------------------------------- JSON API
# (Module 8 exposed as a small REST endpoint for programmatic / test use)
@app.route("/api/match", methods=["POST"])
@login_required
def api_match():
    payload = request.get_json(force=True)
    db = get_db()
    lost = db.execute("SELECT * FROM items WHERE item_id = ?", (payload["lost_item_id"],)).fetchone()
    found = db.execute("SELECT * FROM items WHERE item_id = ?", (payload["found_item_id"],)).fetchone()
    db.close()
    if not lost or not found:
        return jsonify({"error": "item not found"}), 404
    result = compute_match(dict(lost), dict(found), UPLOAD_DIR)
    return jsonify(result)


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db(reset=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=5000)
