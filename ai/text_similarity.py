"""
Module 5 -- NLP Similarity Engine
----------------------------------
Compares free-text item descriptions using a TF-IDF vector space model
with cosine similarity, run on top of the synonym-normalized text from
`preprocessing.normalize_text`. This lightweight approach was chosen
deliberately for the prototype because it needs no internet connection
or pretrained-model download, runs in milliseconds, and -- combined
with the synonym expansion step -- already resolves the motivating
example from Section 1 ("black Lenovo laptop bag" vs "black computer
backpack"). The same interface (`text_similarity(a, b)`) can later be
swapped for sentence-embedding models (e.g. Sentence-BERT) without
touching the matching engine.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ai.preprocessing import normalize_text


def text_similarity(description_a: str, description_b: str) -> float:
    """Return a 0..1 semantic similarity score between two descriptions."""
    a = normalize_text(description_a)
    b = normalize_text(description_b)

    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    try:
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform([a, b])
        score = cosine_similarity(tfidf[0], tfidf[1])[0][0]
    except ValueError:
        # e.g. both strings reduced to nothing after stopword removal
        return 0.0

    return float(max(0.0, min(1.0, score)))


def batch_text_similarity(query: str, candidates: list[str]) -> list[float]:
    """Vectorize the query against many candidates at once (used by the
    matching engine when a new report is compared against every open
    report of the opposite type)."""
    norm_query = normalize_text(query)
    norm_candidates = [normalize_text(c) for c in candidates]

    corpus = [norm_query] + norm_candidates
    if not norm_query or all(not c for c in norm_candidates):
        return [0.0] * len(candidates)

    vectorizer = TfidfVectorizer()
    try:
        tfidf = vectorizer.fit_transform(corpus)
    except ValueError:
        return [0.0] * len(candidates)

    sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
    return [float(max(0.0, min(1.0, s))) for s in sims]
