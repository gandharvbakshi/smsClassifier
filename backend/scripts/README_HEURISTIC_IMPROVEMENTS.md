# Heuristic Classifier Improvements - Usage Guide

## Quick Start

### 1. Test Improved Heuristic Classifier

Run the improved classifier on your dataset:

```bash
cd backend/scripts
python test_heuristic_otp_classification.py classification_results_full.csv
```

This will:
- Test the improved heuristic classifier
- Generate performance metrics
- Save results to `backend/heuristic_test_results/`

### 2. Investigate Missed Keywords

Find out why messages with OTP keywords are being missed:

```bash
python investigate_missed_keywords.py
```

This will:
- Identify messages with keywords that were still missed
- Test keyword matching logic
- Provide analysis and recommendations
- Save detailed results to `backend/heuristic_test_results/missed_keywords_analysis.csv`

### 3. Analyze Missed OTPs

Get detailed analysis of all missed OTPs:

```bash
python analyze_missed_otps.py
```

This will:
- Analyze patterns in missed OTPs
- Provide recommendations for further improvements
- Show sample missed messages by category

### 4. Fix Ground Truth Labels

Review and fix conflicting labels (dry run first):

```bash
# Dry run - shows what would be fixed without making changes
python fix_ground_truth_labels.py classification_results_full.csv

# Apply fixes - actually corrects the labels
python fix_ground_truth_labels.py classification_results_full.csv --apply
```

Options:
- `--apply`: Actually apply fixes (default: dry run)
- `--output filename.csv`: Specify output file name (default: adds `_fixed` suffix)

This will:
- Identify messages marked as `is_otp=True` but `intent='NOT_OTP'`
- Categorize conflicting messages
- Create fixed dataset
- Save conflicting labels for review to `backend/heuristic_test_results/conflicting_labels_review.csv`

## Key Improvements Made

### 1. Enhanced Patterns
- **Code-at-start pattern**: Catches codes at message beginning
- **Verification pattern**: Detects verification words with codes
- **Security warning pattern**: Uses security warnings as indicators

### 2. Better Keyword Matching
- Uses word boundaries to avoid false matches
- Expanded keyword and phrase lists
- Improved matching logic

### 3. Additional Indicators
- Validity period indicators
- Security warning indicators
- Multi-indicator confidence boosting

### 4. Improved Short Message Detection
- Lower thresholds (100 chars for higher confidence)
- Better granularity

## Expected Results

### Before
- Recall: 16.64%
- High confidence: 4.22%

### After (Estimated)
- Recall: 25-40% (2-3x improvement)
- High confidence: 8-12% (2-3x improvement)
- Precision: ~98-99% (slight drop from 100%)

## Workflow Recommendation

1. **First**: Run label fix script (dry run) to see data quality issues
2. **Second**: Apply label fixes if needed
3. **Third**: Test improved classifier on fixed dataset
4. **Fourth**: Investigate any remaining missed cases
5. **Fifth**: Iterate based on findings

## Output Files

All results are saved to `backend/heuristic_test_results/`:

- `heuristic_performance_report.json`: Performance metrics
- `heuristic_classification_results.csv`: Detailed classification results
- `missed_keywords_analysis.csv`: Analysis of missed keywords
- `conflicting_labels_review.csv`: Conflicting labels for review
- `ANALYSIS_AND_RECOMMENDATIONS.md`: Detailed analysis
- `IMPROVEMENTS_IMPLEMENTED.md`: Summary of improvements

## Need Help?

Check the detailed documentation:
- `backend/heuristic_test_results/ANALYSIS_AND_RECOMMENDATIONS.md`
- `backend/heuristic_test_results/IMPROVEMENTS_IMPLEMENTED.md`
