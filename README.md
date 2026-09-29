# Intelligent Lost & Found — AI-Powered Object Matching and Recovery System

A working prototype built directly from the attached MCA mini-project synopsis
("Intelligent Lost & Found: AI-Powered Object Matching and Recovery System",
SY MCA, Div C, MIT-WPU Pune). It implements every module listed in Section 9
of the synopsis and follows the four-layer architecture from Section 8.

## Quick start

```bash
cd lost_found_ai
pip install -r requirements.txt

python db.py           # creates lostfound.db from schema.sql
python seed_demo.py    # loads demo users + the Section 10.2 test scenario
python app.py           # http://127.0.0.1:5000
```

Demo logins (created by `seed_demo.py`):

| Email | Password | Role |
|---|---|---|
| harsh@example.edu | password123 | user |
| mihir@example.edu | password123 | user |
| ananya@example.edu | password123 | user |
| admin@example.edu | admin123 | admin |

Log in as `harsh@example.edu`, open **Dashboard → My Reports → View matches**
on the "Black Lenovo laptop bag" report to see the AI engine surface the
differently-worded found report from Section 1/10.2 of the synopsis
("black computer backpack ... found outside the computer laboratory") as a
ranked, explained potential match — then submit a claim and, as
`admin@example.edu`, verify it from **Admin → Claim Moderation Queue**.

To sanity-check the scoring model in isolation (no server needed):

```bash
python evaluate.py     # Section 10.1 precision / false-positive-rate / timing
```

## How the synopsis maps onto this codebase

| Synopsis section | Implementation |
|---|---|
| §8.1 Presentation layer | `templates/`, `static/style.css` (server-rendered, no external CDN dependency) |
| §8.2 Application/API layer | `app.py` (Flask routes) + `/api/match` JSON endpoint |
| §8.3 AI Processing layer | `ai/` package (see below) |
| §8.4 Data layer | `db.py` + `schema.sql` (SQLite; swap `db.py` for MySQL/Postgres later without touching callers) |
| §8.6 Entities | `users`, `items`, `matches`, `claims`, `notifications`, `locations` tables in `schema.sql` |
| Module 1 | `app.py` — `register`, `login`, `logout`, `login_required` / `admin_required` |
| Module 2 & 3 | `app.py` — `report_lost`, `report_found`, `_handle_report` |
| Module 4 | `ai/preprocessing.py` — text normalization, synonym expansion, image loading |
| Module 5 | `ai/text_similarity.py` — TF-IDF + cosine similarity |
| Module 6 | `ai/image_similarity.py` — HSV colour histogram + ORB feature matching |
| Module 7 | `ai/attribute_scoring.py` — category / colour / location / time-proximity scoring |
| Module 8 | `ai/matching_engine.py` — weighted score, classification bands, explanations |
| Module 9 | `app.py` — `_notify`, notification bell + `/notifications/read/<id>` |
| Module 10 | `app.py` — `submit_claim`, `review_claim` (verify / reject / needs-info) |
| Module 11 | `app.py` — `admin_dashboard` (counts, category/location breakdown, claim queue) |
| §5.4 scoring formula | `ai/matching_engine.py::DEFAULT_WEIGHTS` = 30/30/15/10/5/10 exactly as specified |
| §5.5 classification bands | `ai/matching_engine.py::classify_score` (90/75/50 cut-offs) |
| §5.6 explainability | `ai/matching_engine.py::_explain` → "reason chips" shown on the matches page |
| §5.7 claim & verification | `submit_claim` requires a non-public identifying detail; ownership never transfers automatically |
| §10.1 evaluation | `evaluate.py` — precision, false-positive rate, recall, response time on a labelled sample |
| §10.2 test scenario | seeded verbatim in `seed_demo.py` (the "black Lenovo laptop bag" / "black computer backpack" pair) |

## Design decisions worth knowing about

- **NLP approach**: the synopsis specifies "a suitable NLP approach" rather
  than mandating a specific model. This prototype uses TF-IDF + cosine
  similarity on synonym-normalized text (`ai/preprocessing.py::SYNONYMS`) so
  it runs instantly with zero external downloads and no internet dependency,
  while still resolving the "laptop bag" vs "computer backpack" example from
  Section 1. `ai/text_similarity.py` exposes a single `text_similarity(a, b)`
  function — swap its internals for a sentence-embedding model (e.g.
  Sentence-BERT / OpenAI embeddings) later without touching any other file.
- **Computer-vision approach**: similarly, image evidence is computed from
  an HSV colour histogram + ORB keypoint matching (classical CV, OpenCV,
  no pretrained weights to download). `ai/image_similarity.py` isolates this
  behind `image_similarity(path_a, path_b)` so it can be swapped for a CNN
  embedding model later.
- **Weights are configurable**, exactly as the synopsis states — they live
  as a plain dict (`DEFAULT_WEIGHTS`) that a future admin settings screen
  could persist per-deployment after evaluating real data.
- **Claims never auto-resolve ownership** (Section 5.7): submitting a claim
  only moves the two linked reports to `matched` status; only an
  administrator verifying the claim moves them to `recovered`.
- `evaluate.py`'s labelled sample is text/attribute-only (no photos), so
  every score there is capped below the 30% image-similarity ceiling — this
  is expected, and the script reports precision/recall at both the 75%
  auto-notify threshold and the 50% manual-review floor so the effect is
  visible rather than hidden.

## Future scope (Section 6.3)

Everything in that list — mobile app, QR/NFC tags, multilingual
descriptions, geospatial maps, deep-learning image retrieval, federated
campuses, fraud detection, cloud storage — was intentionally left out of
this prototype scope and is not implemented here.
