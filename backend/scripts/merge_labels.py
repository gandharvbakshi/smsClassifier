import pandas as pd
import numpy as np

# Read the CSV file
print("Reading merged_standardized.csv...")
df_csv = pd.read_csv('merged_standardized.csv')

# Skip the first row which appears to be a header row
df_csv = df_csv.iloc[1:].reset_index(drop=True)

# Read the Excel file
print("Reading Excel file...")
df_excel = pd.read_excel('Gandharv personal all_conversations_03_11_2025_13h56h59_standardized_labeled.xlsx')

# Create a mapping dictionary from Excel file based on 'sender' column
# Only include rows where is_otp, otp_intent, or share_advice have non-null values
print("Creating mapping from Excel file...")
excel_mapping = {}

for idx, row in df_excel.iterrows():
    sender = row['sender']
    if pd.notna(sender):
        # Store the values if they exist
        mapping_entry = {}
        if pd.notna(row['is_otp']):
            mapping_entry['is_otp'] = row['is_otp']
        if pd.notna(row['otp_intent']):
            mapping_entry['otp_intent'] = row['otp_intent']
        if pd.notna(row['share_advice']):
            mapping_entry['share_advice'] = row['share_advice']
        
        if mapping_entry:  # Only store if at least one value exists
            excel_mapping[sender] = mapping_entry

print(f"Found {len(excel_mapping)} entries with labels in Excel file")

# Convert columns to object type to avoid dtype warnings
df_csv['is_otp'] = df_csv['is_otp'].astype(object)
df_csv['otp_intent'] = df_csv['otp_intent'].astype(object)
df_csv['share_advice'] = df_csv['share_advice'].astype(object)

# Merge the labels into the CSV dataframe
print("Merging labels...")
merged_count = 0
for idx, row in df_csv.iterrows():
    sender = row['sender']
    if sender in excel_mapping:
        mapping = excel_mapping[sender]
        if 'is_otp' in mapping:
            df_csv.at[idx, 'is_otp'] = mapping['is_otp']
        if 'otp_intent' in mapping:
            df_csv.at[idx, 'otp_intent'] = mapping['otp_intent']
        if 'share_advice' in mapping:
            df_csv.at[idx, 'share_advice'] = mapping['share_advice']
        merged_count += 1

print(f"Successfully merged {merged_count} entries")

# Merge synthetic OTP intents from synthetic_otp_intents_with_senders.csv
print("\n" + "="*80)
print("Reading synthetic_otp_intents_with_senders.csv...")
try:
    df_synthetic = pd.read_csv('synthetic_otp_intents_with_senders.csv')
    print(f"Found {len(df_synthetic)} synthetic rows")
    
    # Ensure columns match
    synthetic_cols = set(df_synthetic.columns.tolist())
    csv_cols = set(df_csv.columns.tolist())
    
    if synthetic_cols == csv_cols:
        # Append synthetic rows to the main dataframe
        print("Merging synthetic rows into main dataframe...")
        df_csv = pd.concat([df_csv, df_synthetic], ignore_index=True)
        print(f"Successfully merged {len(df_synthetic)} synthetic rows")
        print(f"Total rows after merging synthetic data: {len(df_csv)}")
    else:
        print("Warning: Column mismatch between files")
        print(f"CSV columns: {csv_cols}")
        print(f"Synthetic columns: {synthetic_cols}")
except FileNotFoundError:
    print("Warning: synthetic_otp_intents_with_senders.csv not found. Skipping...")
except Exception as e:
    print(f"Warning: Error reading synthetic file: {e}")

# Print final value_counts for otp_intent
print("\n" + "="*80)
print("FINAL VALUE COUNTS FOR otp_intent:")
print("="*80)
print(df_csv['otp_intent'].value_counts(dropna=False))
print(f"\nTotal entries: {len(df_csv)}")
print(f"Non-null otp_intent entries: {df_csv['otp_intent'].notna().sum()}")

# Print a sample of 20 entries with 5 per otp_intent category
print("\n" + "="*80)
print("SAMPLE OF 20 ENTRIES (5 per otp_intent category):")
print("="*80)

# Get unique otp_intent categories (excluding NaN)
otp_categories = df_csv['otp_intent'].dropna().unique()
print(f"\nFound {len(otp_categories)} unique otp_intent categories: {otp_categories.tolist()}")

# Sample 5 entries per category (or as many as available if less than 5)
samples_dict = {}
total_sampled = 0

for category in otp_categories:
    category_df = df_csv[df_csv['otp_intent'] == category]
    if len(category_df) >= 5:
        sampled = category_df.sample(n=5, random_state=42)
    else:
        sampled = category_df
    samples_dict[category] = sampled
    total_sampled += len(sampled)

# Display samples - prioritize categories with enough entries
print("\n" + "-"*80)
for category in sorted(samples_dict.keys()):
    sampled = samples_dict[category]
    print(f"\nCategory: {category} ({len(sampled)} entries)")
    for idx, row in sampled.iterrows():
        print(f"\n  Entry {idx}:")
        print(f"    sender: {str(row['sender'])[:100]}...")
        print(f"    is_otp: {row['is_otp']}")
        print(f"    otp_intent: {row['otp_intent']}")
        print(f"    share_advice: {row['share_advice']}")

print(f"\nTotal sampled entries: {total_sampled}")

# Save the merged dataframe
print("\n" + "="*80)
print("Saving merged file as merged_standardized_partially_labeled.csv...")
df_csv.to_csv('merged_standardized_partially_labeled.csv', index=False)
print("File saved successfully!")

# Save rows with otp_intent labels to a separate CSV file
print("\n" + "="*80)
print("Extracting rows with otp_intent labels...")
df_otp_intent_only = df_csv[df_csv['otp_intent'].notna()].copy()
print(f"Found {len(df_otp_intent_only)} rows with otp_intent labels")
print("Saving to otp_intent_only_rows.csv...")
df_otp_intent_only.to_csv('otp_intent_only_rows.csv', index=False)
print("File saved successfully!")

print("\n" + "="*80)
print("SUMMARY:")
print("="*80)
print(f"Total rows in merged file: {len(df_csv)}")
print(f"Rows with is_otp labels: {df_csv['is_otp'].notna().sum()}")
print(f"Rows with otp_intent labels: {df_csv['otp_intent'].notna().sum()}")
print(f"Rows with share_advice labels: {df_csv['share_advice'].notna().sum()}")
print(f"Rows saved to otp_intent_only_rows.csv: {len(df_otp_intent_only)}")

