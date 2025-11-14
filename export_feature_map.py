import json
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VECTOR_PATH = ROOT / "android_model_exports" / "tfidf_vectorizer.pkl"
OUTPUT_PATH = ROOT / "android_sms_classifier" / "app" / "src" / "main" / "assets" / "feature_map.json"

# heuristic feature count must stay in sync with FeatureExtractor
HEURISTIC_FEATURE_COUNT = 23

with VECTOR_PATH.open("rb") as f:
    vectorizer = pickle.load(f)

if not hasattr(vectorizer, "vocabulary_"):
    raise ValueError("Vectorizer does not expose a vocabulary_.")

vocab = {term: int(idx) for term, idx in vectorizer.vocabulary_.items()}

feature_map = {
    "vocab": vocab,
    "heuristicFeatureCount": HEURISTIC_FEATURE_COUNT,
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(feature_map, f, ensure_ascii=False)

print(f"Saved feature map with {len(vocab)} terms to {OUTPUT_PATH}")
