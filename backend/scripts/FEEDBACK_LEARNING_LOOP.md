# Feedback Learning Loop

This loop keeps production changes review-gated.

1. Pull production feedback into `feedback_corpus/`.
2. Build a deduped review queue:
   `python backend/scripts/feedback_learning_loop.py queue`
   The default scan ignores generated `review_queue.jsonl` and
   `reviewed_feedback_regression_cases.jsonl` files to avoid re-ingesting its
   own artifacts.
3. Review `feedback_corpus/review_queue.jsonl` and mark rows as `accepted` or `rejected`.
4. Export accepted rows as regression cases:
   `python backend/scripts/feedback_learning_loop.py regressions`
5. Run the classifier regression suite:
   `python backend/scripts/run_feedback_regressions.py`

Accepted feedback cases are loaded from
`feedback_corpus/reviewed_feedback_regression_cases.jsonl` by default.

Do not train or deploy a new model directly from raw user feedback. Treat raw
reports as signals, reviewed rows as labels, and regression results as the
release gate.
