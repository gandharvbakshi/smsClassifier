import os
import sys
import pandas as pd


def create_sample(
    source_path: str = "classification_results_with_phishing_llm.csv",
    sample_size: int = 1000,
    output_suffix: str = "_1K_sample",
    random_seed: int = 42,
) -> str:
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found: {source_path}")

    df = pd.read_csv(source_path)
    if df.empty:
        raise ValueError(f"Source file '{source_path}' is empty.")

    sample_count = min(sample_size, len(df))
    sample_df = df.sample(n=sample_count, random_state=random_seed)

    base, ext = os.path.splitext(source_path)
    output_path = f"{base}{output_suffix}{ext or '.csv'}"
    sample_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    return output_path


def main():
    source = "classification_results_with_phishing_llm.csv"
    if len(sys.argv) > 1:
        source = sys.argv[1]

    try:
        output = create_sample(source_path=source)
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    print(f"Sample written to {output}")


if __name__ == "__main__":
    main()

