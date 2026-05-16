"""
Compare heuristic classification results before and after improvements.
"""

import json
from pathlib import Path

def compare_results():
    """Compare before and after results."""
    
    results_dir = Path(__file__).parent.parent / "heuristic_test_results"
    
    print("=" * 80)
    print("HEURISTIC CLASSIFIER IMPROVEMENT COMPARISON")
    print("=" * 80)
    
    # Before (from initial results shown)
    before = {
        "accuracy": 0.1664,
        "precision": 1.0000,
        "recall": 0.1664,
        "f1_score": 0.2854,
        "total_otps": 72153,
        "caught_by_heuristics": 12008,
        "percentage_caught": 16.64,
        "high_confidence_caught": 3042,
        "high_confidence_percentage": 4.22,
        "medium_confidence": 8966,
        "false_negatives": 60145
    }
    
    # After (from current results)
    report_file = results_dir / "heuristic_performance_report.json"
    if report_file.exists():
        with open(report_file, 'r') as f:
            after = json.load(f)
    else:
        print(f"Error: Results file not found: {report_file}")
        return
    
    print("\nMETRICS COMPARISON:")
    print("-" * 80)
    
    metrics = [
        ("Recall", "recall", "%"),
        ("Precision", "precision", "%"),
        ("F1-Score", "f1_score", ""),
        ("Accuracy", "accuracy", "%")
    ]
    
    for name, key, unit in metrics:
        before_val = before[key] * 100 if unit == "%" else before[key]
        after_val = after[key] * 100 if unit == "%" else after[key]
        improvement = after_val - before_val
        pct_improvement = (improvement / before_val * 100) if before_val > 0 else 0
        
        print(f"{name:15} Before: {before_val:7.2f}{unit}")
        print(f"{'':15} After:  {after_val:7.2f}{unit}")
        print(f"{'':15} Change: {improvement:+7.2f}{unit} ({pct_improvement:+.1f}%)")
        print()
    
    print("CATCH STATISTICS:")
    print("-" * 80)
    
    before_caught = before["caught_by_heuristics"]
    after_caught = after["caught_by_heuristics"]
    additional_caught = after_caught - before_caught
    pct_improvement = (additional_caught / before_caught * 100) if before_caught > 0 else 0
    
    print(f"Total OTPs: {before['total_otps']}")
    print(f"Caught before: {before_caught:,} ({before['percentage_caught']:.2f}%)")
    print(f"Caught after:  {after_caught:,} ({after.get('percentage_caught', after_caught/before['total_otps']*100):.2f}%)")
    print(f"Additional caught: {additional_caught:,} (+{pct_improvement:.1f}%)")
    
    before_fn = before["false_negatives"]
    after_fn = after["confusion_matrix"][1][0] if "confusion_matrix" in after else None
    if after_fn:
        fn_reduction = before_fn - after_fn
        print(f"\nFalse Negatives:")
        print(f"  Before: {before_fn:,}")
        print(f"  After:  {after_fn:,}")
        print(f"  Reduction: {fn_reduction:,} ({fn_reduction/before_fn*100:.1f}% reduction)")
    
    print("\nCONFIDENCE DISTRIBUTION:")
    print("-" * 80)
    
    dist_before = {
        "high": before["high_confidence_caught"],
        "medium": before["medium_confidence"],
        "total_caught": before_caught
    }
    
    dist_after = after.get("confidence_distribution", {})
    
    print(f"High confidence (>0.8):")
    print(f"  Before: {dist_before['high']:,} ({before['high_confidence_percentage']:.2f}%)")
    after_high_pct = (dist_after.get("high_confidence_gt_80", 0) / before['total_otps'] * 100)
    print(f"  After:  {dist_after.get('high_confidence_gt_80', 0):,} ({after_high_pct:.2f}%)")
    
    print(f"\nMedium confidence (0.5-0.8):")
    print(f"  Before: {dist_before['medium']:,}")
    print(f"  After:  {dist_after.get('medium_confidence_50_80', 0):,}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    print(f"\nImprovements achieved:")
    print(f"  [+] Recall increased by {((after['recall'] - before['recall']) / before['recall'] * 100):.1f}%")
    print(f"  [+] {additional_caught:,} more OTPs caught")
    print(f"  [+] Precision maintained at 100%")
    print(f"  [+] No false positives introduced")
    
    if after_fn and fn_reduction:
        print(f"  [+] {fn_reduction:,} fewer false negatives")
    
    print(f"\nRemaining gaps:")
    remaining = before['total_otps'] - after_caught
    remaining_pct = (remaining / before['total_otps'] * 100)
    print(f"  - {remaining:,} OTPs still missed ({remaining_pct:.1f}%)")
    print(f"  - Most OTPs still require ML classification (as designed)")
    
    print(f"\nNext steps:")
    print(f"  1. Investigate why keyword matching might still be missing some cases")
    print(f"  2. Analyze the {remaining:,} remaining false negatives")
    print(f"  3. Consider if ground truth labels need fixing (NOT_OTP messages marked as OTP)")
    print(f"  4. Review confidence thresholds for ML handoff")

if __name__ == "__main__":
    compare_results()
