import pandas as pd

SOURCE_FILE = "classification_results_with_phishing.csv"
VERIFIED_FILE = "classification_results_with_phishing_verified.csv"
OUTPUT_FILE = "phishing_ground_truth_100.csv"


def load_frames():
    source = pd.read_csv(SOURCE_FILE)
    verified = pd.read_csv(VERIFIED_FILE)

    if "needs_manual_review" in verified.columns:
        verified_pos = verified[(verified["needs_manual_review"] == False) & (verified["is_phishing"] == True)]
        verified_neg = verified[(verified["needs_manual_review"] == False) & (verified["is_phishing"] == False)]
    else:
        verified_pos = verified[verified["is_phishing"] == True]
        verified_neg = verified[verified["is_phishing"] == False]

    source_pos = source[source["is_phishing"] == True]
    source_neg = source[source["is_phishing"] == False]

    if not verified_pos.empty:
        source_pos = source_pos[~source_pos["original_index"].isin(verified_pos["original_index"])]
    if not verified_neg.empty:
        source_neg = source_neg[~source_neg["original_index"].isin(verified_neg["original_index"])]

    pos_frames = []
    neg_frames = []

    if not verified_pos.empty:
        pos_frames.append(verified_pos[["original_index", "sms_text", "predicted_is_otp", "predicted_otp_intent", "is_phishing"]])
    if not source_pos.empty:
        pos_frames.append(source_pos[["original_index", "sms_text", "predicted_is_otp", "predicted_otp_intent", "is_phishing"]])

    if not verified_neg.empty:
        neg_frames.append(verified_neg[["original_index", "sms_text", "predicted_is_otp", "predicted_otp_intent", "is_phishing"]])
    if not source_neg.empty:
        neg_frames.append(source_neg[["original_index", "sms_text", "predicted_is_otp", "predicted_otp_intent", "is_phishing"]])

    pos_df = pd.concat(pos_frames, ignore_index=True) if pos_frames else pd.DataFrame()
    neg_df = pd.concat(neg_frames, ignore_index=True) if neg_frames else pd.DataFrame()
    return pos_df, neg_df


def main():
    pos_df, neg_df = load_frames()

    if len(pos_df) < 80:
        raise SystemExit(f"Only {len(pos_df)} positive phishing rows available; need 80.")

    pos_sample = pos_df.sample(n=80, random_state=42)
    neg_sample = neg_df.sample(n=min(20, len(neg_df)), random_state=42)

    combined = pd.concat([pos_sample, neg_sample], ignore_index=True).sample(frac=1, random_state=7)
    combined.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    positives = int((combined["is_phishing"] == True).sum())
    negatives = len(combined) - positives
    print(f"Saved {len(combined)} rows to {OUTPUT_FILE} ({positives} positives, {negatives} negatives)")


if __name__ == "__main__":
    main()


