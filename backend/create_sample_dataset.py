import pandas as pd
import os

# Configuration
INPUT_FILE = r'd:\Projects\SMS datasets and project\backend\data\classification_results_with_phishing_llm_balanced_with_sender.csv'
OUTPUT_FILE = r'd:\Projects\SMS datasets and project\backend\data\sample_10k.csv'
TARGET_TOTAL = 10000
TARGET_FALSE = 7000
TARGET_TRUE = 3000

print("Loading dataset...")
if not os.path.exists(INPUT_FILE):
    print(f"Error: Input file not found at {INPUT_FILE}")
    exit(1)

df = pd.read_csv(INPUT_FILE, low_memory=False)
print(f"Loaded {len(df)} rows.")

# Ensure columns exist (using the names found in previous analysis)
# Note: Previous analysis showed columns: 'predicted_is_otp', 'predicted_otp_intent'
if 'predicted_is_otp' not in df.columns or 'predicted_otp_intent' not in df.columns:
    print("Error: Required columns 'predicted_is_otp' or 'predicted_otp_intent' not found.")
    print("Columns:", df.columns.tolist())
    exit(1)

# Split by OTP status
# Handle potential string/boolean mixed types safely
df['predicted_is_otp_bool'] = df['predicted_is_otp'].astype(str).str.upper() == 'TRUE'
df_false = df[~df['predicted_is_otp_bool']].copy()
df_true = df[df['predicted_is_otp_bool']].copy()

print(f"Found {len(df_false)} False rows and {len(df_true)} True rows.")

# Sample False rows (Random 7k)
if len(df_false) >= TARGET_FALSE:
    df_false_sample = df_false.sample(n=TARGET_FALSE, random_state=42)
else:
    print(f"Warning: Not enough False rows ({len(df_false)}) to sample {TARGET_FALSE}. Taking all.")
    df_false_sample = df_false

# Sample True rows (Balanced 3k)
# Strategy: Cap the large categories to ensure smaller ones are represented.
# We want ~3000 total.
# Let's check counts of intents in df_true
intent_counts = df_true['predicted_otp_intent'].value_counts()
print("\nIntent counts in True set:")
print(intent_counts)

# We have ~8 categories. 3000 / 8 = 375.
# Some are smaller (300), some are huge (1920).
# We will take all rows from categories <= 400.
# We will sample 400 from categories > 400.
# Then fill the remainder from the largest categories proportionally or just from the largest.

selected_true_rows = []
remaining_slots = TARGET_TRUE
categories = intent_counts.index.tolist()

# First pass: Take up to 400 from each
# Actually, let's do a dynamic allocation to be more robust.
# If we just cap at X, we might not reach 3000 if many are small.
# Let's try to fill 3000.
# If we take all small ones, how many slots left?
# Let's try to give every category at least min(count, 350) rows.
# Then distribute the rest.

# Better approach:
# 1. Take min(count, 350) for everyone.
# 2. Count how many selected.
# 3. Distribute remaining slots to categories that have more data available.

# Step 1: Base allocation
base_allocation = {}
rows_indices_to_take = set()

for intent in categories:
    available = intent_counts[intent]
    take = min(available, 350)
    base_allocation[intent] = take
    
    # Get indices for this intent
    intent_indices = df_true[df_true['predicted_otp_intent'] == intent].index.tolist()
    # Sample 'take' indices randomly
    import random
    random.seed(42)
    selected = random.sample(intent_indices, take)
    rows_indices_to_take.update(selected)

current_total = len(rows_indices_to_take)
needed = TARGET_TRUE - current_total
print(f"\nAfter base allocation (min 350), selected {current_total} rows. Need {needed} more.")

# Step 2: Fill remaining from categories that have spare capacity
# We want to keep it balanced, so we should distribute the 'needed' slots among those who can provide them.
# Who has spare capacity?
spare_capacity = {}
for intent in categories:
    available = intent_counts[intent]
    already_taken = base_allocation[intent]
    spare = available - already_taken
    if spare > 0:
        spare_capacity[intent] = spare

print("Spare capacity:", spare_capacity)

# Distribute 'needed' proportionally to spare capacity? Or just equally?
# If we want to avoid the largest one dominating, we should try to cap.
# But if only the largest one has significant spare capacity, we have to take from it.
# Let's just sample from the pool of ALL remaining rows in df_true (excluding already selected).
# This naturally pulls from the larger categories.

remaining_indices = df_true.index.difference(list(rows_indices_to_take))
if len(remaining_indices) >= needed:
    # Sample 'needed' from remaining
    extra_indices = pd.Index(remaining_indices).to_series().sample(n=needed, random_state=42).tolist()
    rows_indices_to_take.update(extra_indices)
else:
    print(f"Warning: Not enough True rows to reach {TARGET_TRUE}. Taking all {len(df_true)}.")
    rows_indices_to_take.update(remaining_indices)

df_true_sample = df_true.loc[list(rows_indices_to_take)]

print(f"\nFinal True sample size: {len(df_true_sample)}")
print("Final Intent Distribution:")
print(df_true_sample['predicted_otp_intent'].value_counts())

# Combine
df_final = pd.concat([df_false_sample, df_true_sample])
# Shuffle
df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

print(f"\nCreated sample dataset with {len(df_final)} rows.")
print(df_final['predicted_is_otp_bool'].value_counts())

# Save
df_final.drop(columns=['predicted_is_otp_bool'], inplace=True) # Cleanup helper
df_final.to_csv(OUTPUT_FILE, index=False)
print(f"Saved to {OUTPUT_FILE}")
