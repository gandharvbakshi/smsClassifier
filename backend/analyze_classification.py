import pandas as pd
import os
import sys

# Force unbuffered output
sys.stdout.reconfigure(encoding='utf-8')

file_path = r'd:\Projects\SMS datasets and project\backend\data\classification_results_with_phishing_llm_balanced_with_sender.csv'
output_file_path = r'd:\Projects\SMS datasets and project\backend\analysis_results_v3.txt'

print("STARTING SCRIPT")

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

try:
    print(f"Reading CSV from {file_path}...")
    # Read full file
    df = pd.read_csv(file_path, low_memory=False)
    print(f"READ DONE. Loaded {len(df)} rows.")

    print(f"Starting analysis... Writing to {output_file_path}")
    
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(f"Loaded DataFrame with {len(df)} rows.\n")
        f.write(f"Columns: {df.columns.tolist()}\n")

        f.write("\n" + "="*30 + "\n")
        f.write("VALUE COUNTS\n")
        f.write("="*30 + "\n")

        # Updated column names based on file inspection
        cols_to_check = ['predicted_is_otp', 'predicted_otp_intent', 'is_phishing_original']
        for col in cols_to_check:
            if col in df.columns:
                f.write(f"\nValue Counts for '{col}':\n")
                f.write(df[col].value_counts(dropna=False).to_string() + "\n")
            else:
                f.write(f"\nColumn '{col}' not found.\n")

        f.write("\n" + "="*30 + "\n")
        f.write("MISMATCH ANALYSIS (predicted_is_otp=True but predicted_otp_intent=NOT_OTP)\n")
        f.write("="*30 + "\n")

        if 'predicted_is_otp' in df.columns and 'predicted_otp_intent' in df.columns:
            # Handle boolean or string 'True'
            otp_condition = df['predicted_is_otp'].astype(str).str.upper() == 'TRUE'
            intent_condition = df['predicted_otp_intent'] == 'NOT_OTP'
            
            mismatch_df = df[otp_condition & intent_condition]
            
            f.write(f"\nFound {len(mismatch_df)} rows matching the criteria.\n")
            
            if not mismatch_df.empty:
                f.write("\nFirst 20 matching rows:\n")
                display_cols = ['sms_text', 'predicted_is_otp', 'predicted_otp_intent']
                if 'sender' in df.columns:
                    display_cols.append('sender')
                    
                f.write(mismatch_df[display_cols].head(20).to_string() + "\n")
                
                if len(mismatch_df) > 0:
                    csv_output = r'd:\Projects\SMS datasets and project\backend\data\otp_mismatch_analysis.csv'
                    mismatch_df.to_csv(csv_output, index=False)
                    f.write(f"\nFull mismatch dataset saved to: {csv_output}\n")
        else:
            f.write("Cannot perform mismatch analysis: missing required columns.\n")
            
    print(f"Analysis complete. Output written to {output_file_path}")
    print("WRITE DONE")

except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    traceback.print_exc()
