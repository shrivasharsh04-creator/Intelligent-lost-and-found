-- =====================================================================
-- Intelligent Lost & Found : AI-Powered Object Matching and Recovery
-- Data Layer -- Schema (Section 8.6 of the project synopsis)
-- =====================================================================

DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS claims;
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    role          TEXT NOT NULL DEFAULT 'user',   -- 'user' | 'admin'
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    building    TEXT NOT NULL,
    floor       TEXT,
    area        TEXT,
    latitude    REAL,
    longitude   REAL
);

CREATE TABLE items (
    item_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type     TEXT NOT NULL CHECK (report_type IN ('lost', 'found')),
    category        TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    colour          TEXT,
    location        TEXT,
    date_time       TEXT NOT NULL,                 -- ISO datetime of loss/find
    unique_id       TEXT,                           -- optional serial no. / roll no. etc.
    image_reference TEXT,                           -- filename in /uploads
    status          TEXT NOT NULL DEFAULT 'open',   -- open | matched | claimed | recovered | closed
    user_id         INTEGER NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE matches (
    match_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    lost_item_id    INTEGER NOT NULL,
    found_item_id   INTEGER NOT NULL,
    text_score      REAL NOT NULL,
    image_score     REAL NOT NULL,
    location_score  REAL NOT NULL,
    category_score  REAL NOT NULL,
    colour_score    REAL NOT NULL,
    time_score      REAL NOT NULL,
    total_score     REAL NOT NULL,
    match_category  TEXT NOT NULL,   -- very_strong | strong | possible | low
    explanation     TEXT,            -- JSON list of human-readable reasons
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (lost_item_id)  REFERENCES items(item_id),
    FOREIGN KEY (found_item_id) REFERENCES items(item_id),
    UNIQUE (lost_item_id, found_item_id)
);

CREATE TABLE claims (
    claim_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id            INTEGER NOT NULL,
    claimant_id         INTEGER NOT NULL,
    verification_details TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending', -- pending | verified | rejected | needs_info
    reviewed_by         INTEGER,
    reviewed_at         TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (claimant_id) REFERENCES users(user_id),
    FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
);

CREATE TABLE notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    match_id        INTEGER,
    message         TEXT NOT NULL,
    read_status     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);
