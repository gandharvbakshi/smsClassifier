import pandas as pd
import re
import random
import html
from pathlib import Path
from typing import Union, List

# -------------------------------------------------
# Helper: robust table reader (CSV / Excel / many encodings)
# -------------------------------------------------
def load_table(path: Union[str, Path]) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in [".xls", ".xlsx"]:
        # For Excel files, you might need: pip install openpyxl xlrd
        try:
            return pd.read_excel(path)
        except Exception as e:
            raise RuntimeError(f"Error reading Excel file {path}: {e}")
    else:
        encodings = ["utf-8", "utf-8-sig", "latin1", "utf-16"]
        seps = [",", "\t", ";"]
        last_err = None
        for enc in encodings:
            for sep in seps:
                try:
                    df = pd.read_csv(
                        path,
                        encoding=enc,
                        sep=sep,
                        engine="python",
                    )
                    return df
                except Exception as e:
                    last_err = e
                    continue
        raise RuntimeError(f"Error reading CSV file {path}: {last_err}")


# -------------------------------------------------
# Heuristic column mapping
# -------------------------------------------------
COL_CANDIDATES = {
    "id": ["id", "msg_id", "message_id", "mid", "sms_id", "id_str"],
    "sender": ["sender", "from", "address", "phone", "source", "originator"],
    "body": ["body", "text", "message", "msg", "content", "sms", "conversation", "message_body"],
    "timestamp": ["timestamp", "time", "date", "datetime", "sent_at", "created_at", "ts"],
}

def find_first_column(df: pd.DataFrame, candidates: List[str]) -> Union[str, None]:
    # exact match (case-insensitive)
    for c in candidates:
        for col in df.columns:
            if col.strip().lower() == c:
                return col
    # fuzzy: substring match
    for c in candidates:
        for col in df.columns:
            if c in col.strip().lower():
                return col
    return None


# -------------------------------------------------
# Anonymization regexes (amounts, balances, masked cards)
# -------------------------------------------------
currency_prefix_re = re.compile(
    r"(?P<prefix>(?:Rs\.?|INR|₹|rupee[s]?|Rupee)\s*[:\-]?\s*)(?P<amt>[0-9\.,]+)",
    flags=re.IGNORECASE,
)

currency_suffix_re = re.compile(
    r"(?P<amt>\b[0-9\.,]+\b)\s*(?P<suffix>(?:INR|Rs|rupees|Rupee))",
    flags=re.IGNORECASE,
)

balance_re = re.compile(
    r"(?P<prefix>\b(?:balance|bal|acct bal|available balance|bal:)\b[^0-9]{0,8}?)(?P<num>[0-9\.,]{3,})",
    flags=re.IGNORECASE,
)

# masked card numbers like XX7007, xxxx1234, X2345, X1234
card_number_re = re.compile(r"\bX{1,4}\d{3,5}\b", flags=re.IGNORECASE)

# generic 10-digit numbers (e.g., phone numbers)
ten_digit_number_re = re.compile(r"(?<!\d)\d{10}(?!\d)")

# explicit sensitive numbers to anonymize wherever they appear (with optional country prefix)
explicit_numbers_re = re.compile(r"(\+?91[\-\s]?)?(9739097525|9513908010)")

# Indian vehicle registration numbers like KA03MW7329, KA 03 MW 7329, KA-03-MW-7329
vehicle_plate_re = re.compile(
    r"\b([A-Za-z]{2})(\s*-?\s*)(\d{2})(\s*-?\s*)([A-Za-z]{1,3})(\s*-?\s*)(\d{4})\b"
)

# contexts like "... Credit Card 7007" or "... Debit Card 1234"
credit_card_last4_re = re.compile(
    r"(?i)\b(credit\s*card|debit\s*card)[^\d]{0,12}(\d{4})\b"
)


def jumble_digits_preserve_format(num_str: str) -> str:
    new_chars = []
    for ch in num_str:
        if ch.isdigit():
            new_chars.append(str(random.randint(0, 9)))
        else:
            new_chars.append(ch)
    return "".join(new_chars)


def repl_currency_prefix(match: re.Match) -> str:
    prefix = match.group("prefix")
    amt = match.group("amt")
    return prefix + jumble_digits_preserve_format(amt)


def repl_currency_suffix(match: re.Match) -> str:
    amt = match.group("amt")
    suf = match.group("suffix")
    return jumble_digits_preserve_format(amt) + " " + suf


def repl_balance(match: re.Match) -> str:
    prefix = match.group("prefix")
    num = match.group("num")
    return prefix + jumble_digits_preserve_format(num)


def jumble_card_number(match: re.Match) -> str:
    s = match.group(0)
    prefix_match = re.match(r"^[Xx]+", s)
    prefix_str = prefix_match.group(0) if prefix_match else ""
    digits = s[len(prefix_str):]
    new_digits = "".join(str(random.randint(0, 9)) for _ in digits)
    return prefix_str + new_digits


def anonymize_amounts_and_cards(text: str) -> str:
    if not isinstance(text, str):
        return text
    s = html.unescape(text)
    # currency replacements
    s = currency_prefix_re.sub(repl_currency_prefix, s)
    s = currency_suffix_re.sub(repl_currency_suffix, s)
    s = balance_re.sub(repl_balance, s)
    # card number anonymization
    s = card_number_re.sub(jumble_card_number, s)
    # explicit target numbers (and variants with +91/91- prefix)
    s = explicit_numbers_re.sub(lambda m: jumble_digits_preserve_format(m.group(0)), s)
    # generic contiguous 10-digit numbers
    s = ten_digit_number_re.sub(lambda m: jumble_digits_preserve_format(m.group(0)), s)
    # vehicle registration anonymization (preserve separators and component lengths)
    def repl_vehicle(m: re.Match) -> str:
        state = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in m.group(1))
        sep1 = m.group(2)
        district = ''.join(str(random.randint(0, 9)) for _ in m.group(3))
        sep2 = m.group(4)
        series = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in m.group(5))
        sep3 = m.group(6)
        number = ''.join(str(random.randint(0, 9)) for _ in m.group(7))
        return f"{state}{sep1}{district}{sep2}{series}{sep3}{number}"
    s = vehicle_plate_re.sub(repl_vehicle, s)
    # last 4 digits following Credit/Debit Card context
    def repl_cc_last4(m: re.Match) -> str:
        prefix = m.group(1)
        digits = m.group(2)
        new_digits = ''.join(str(random.randint(0, 9)) for _ in digits)
        return m.group(0)[:m.start(2) - m.start(0)] + new_digits
    s = credit_card_last4_re.sub(lambda m: f"{m.group(1)}{m.group(0)[len(m.group(1)):-4]}" + ''.join(str(random.randint(0,9)) for _ in range(4)), s)
    return s


# -------------------------------------------------
# Simple language detection (Hindi/English/Bangla heuristic)
# -------------------------------------------------
def detect_language_simple(text: str) -> str:
    """
    Very rough heuristic:
    - Devanagari  -> 'hi'
    - Bengali     -> 'bn'
    - Latin       -> 'en'
    - else        -> 'unknown'
    """
    if not isinstance(text, str) or not text.strip():
        return "unknown"

    # Devanagari (Hindi etc.): U+0900–U+097F
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    # Bengali: U+0980–U+09FF
    if re.search(r"[\u0980-\u09FF]", text):
        return "bn"

    # Latin letters
    if re.search(r"[A-Za-z]", text):
        return "en"

    return "unknown"


# -------------------------------------------------
# Main standardization function
# -------------------------------------------------
def standardize_sms_file(input_path: Union[str, Path], output_path: Union[str, Path]):
    input_path = Path(input_path)
    output_path = Path(output_path)

    df_raw = load_table(input_path)
    print(f"\n=== Processing {input_path} ===")
    print("Raw columns:", list(df_raw.columns))

    mapped = {}
    for target, candidates in COL_CANDIDATES.items():
        mapped[target] = find_first_column(df_raw, candidates)

    # Fallback for body: pick the column with the longest average string length
    if mapped["body"] is None:
        avg_len = {
            col: df_raw[col].astype(str).map(len).mean()
            for col in df_raw.columns
        }
        mapped["body"] = max(avg_len, key=avg_len.get)

    # Fallback for sender: try phone-like patterns (for personal datasets)
    if mapped["sender"] is None:
        phone_cols = []
        for col in df_raw.columns:
            try:
                sample = df_raw[col].dropna().astype(str).head(200).tolist()
            except Exception:
                continue
            phone_like = sum(
                1 for s in sample
                if re.search(r"\b(\+?\d{3,4}[\s-]?\d{3,4}|\d{10,12})\b", s)
            )
            if phone_like > 5:
                phone_cols.append((phone_like, col))
        if phone_cols:
            mapped["sender"] = sorted(phone_cols, reverse=True)[0][1]

    # If no id column, we'll synthesize one
    if mapped["id"] is None:
        mapped["id"] = None

    print("Mapped columns:", mapped)

    std_cols = ["id", "sender", "body", "timestamp", "language", "is_otp", "otp_intent", "share_advice"]
    rows = []

    for idx, row in df_raw.iterrows():
        # id
        if mapped["id"] is None:
            id_val = f"{input_path.stem}_row_{idx}"
        else:
            id_val = row.get(mapped["id"], None)

        # sender (might be None for public corpora)
        sender_val = row.get(mapped["sender"], None) if mapped["sender"] else None
        # body
        body_val = row.get(mapped["body"], "")
        # timestamp (often None in public datasets)
        ts_val = row.get(mapped["timestamp"], None) if mapped["timestamp"] else None

        # anonymize amounts and card numbers
        body_an = anonymize_amounts_and_cards(str(body_val))
        sender_an = anonymize_amounts_and_cards(str(sender_val)) if sender_val is not None else None

        # language detection
        lang = detect_language_simple(body_an)

        rows.append(
            {
                "id": id_val,
                "sender": sender_an,
                "body": body_an,
                "timestamp": ts_val,
                "language": lang,
                "is_otp": "",
                "otp_intent": "",
                "share_advice": "",
            }
        )

    df_std = pd.DataFrame(rows, columns=std_cols)
    df_std.to_csv(output_path, index=False)
    print(f"Standardized {len(df_std)} rows to {output_path}")


# -------------------------------------------------
# Merge all standardized CSVs with a priority order
# -------------------------------------------------
def merge_standardized_files(output_path: Union[str, Path] = "merged_standardized.csv"):
    base = Path.cwd()
    std_files = sorted(
        [p for p in base.glob("*_standardized.csv") if p.is_file()],
        key=lambda p: (0 if p.name == "Gandharv personal all_conversations_03_11_2025_13h56h59_standardized.csv" else 1, p.name.lower()),
    )

    if not std_files:
        print("No standardized files found to merge.")
        return

    print("Merging standardized files in order:")
    for p in std_files:
        print(" -", p.name)

    frames = []
    for p in std_files:
        try:
            frames.append(pd.read_csv(p))
        except Exception as e:
            print(f"Skipping {p} due to read error: {e}")

    if not frames:
        print("No files could be read; merge aborted.")
        return

    merged = pd.concat(frames, ignore_index=True)
    output_path = Path(output_path)
    merged.to_csv(output_path, index=False)
    print(f"Merged {len(merged)} rows into {output_path}")

# -------------------------------------------------
# Example usage: run on your attached files
# -------------------------------------------------
if __name__ == "__main__":
    # Put your actual file names/paths here
    files = [
        "balanced_spam_dataset.csv",
        "bangla_smish.csv",
        "Hindi.csv",
        "shshnk158 Multilingual-SMS-spam-detection-using-RNN revisedindiandataset.xls",
        "SMS PHISHING DATASET FOR MACHINE LEARNING AND PATTERN RECOGNITION Dataset_5971.csv",
        "Spam Message Collection.xlsx",
        "Gandharv personal all_conversations_03_11_2025_13h56h59.csv"
    ]

    for f in files:
        in_path = Path(f)
        if not in_path.exists():
            print(f"Skipping {in_path} (not found)")
            continue
        out_path = in_path.with_name(in_path.stem + "_standardized.csv")
        standardize_sms_file(in_path, out_path)

    # After generating standardized files, merge them
    merge_standardized_files("merged_standardized.csv")
