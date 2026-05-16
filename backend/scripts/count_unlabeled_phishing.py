import pandas as pd

df = pd.read_csv("classification_results_with_phishing.csv")
print("Remaining unlabeled is_phishing rows:", df["is_phishing"].isna().sum())

