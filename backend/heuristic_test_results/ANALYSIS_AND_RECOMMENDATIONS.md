# Heuristic Classification Results Analysis

## Summary

The heuristic classifier achieved:
- **Precision: 100%** (1.0000) - No false positives! 
- **Recall: 16.64%** - Only catching 16.64% of OTPs
- **F1-Score: 0.2854**
- **Accuracy: 16.64%**

## Key Findings

### Overall Performance
- **Total OTPs in dataset**: 72,153
- **Caught by heuristics**: 12,008 (16.64%)
- **Missed by heuristics**: 60,145 (83.36%)

### Confidence Distribution
- **High confidence (>0.8)**: 3,042 messages (4.22% of all OTPs)
- **Medium confidence (0.5-0.8)**: 8,966 messages (12.42% of all OTPs)
- **Low confidence (0.0-0.5)**: 0 messages
- **ML needed (0.0 confidence)**: 60,145 messages (83.36% of all OTPs)

### Data Quality Issue

**Important Discovery**: Many messages marked as `ground_truth_is_otp=True` have `ground_truth_intent='NOT_OTP'`. These are transaction notifications, balance updates, and payment confirmations that are NOT actually OTPs.

- When filtering out NOT_OTP intents, only **494 actual OTPs were missed** (0.68%)
- This suggests the ground truth labels may need review

## Strengths

1. **Perfect Precision**: Zero false positives - the heuristics never incorrectly classify non-OTPs as OTPs
2. **High Confidence Accuracy**: The 3,042 high-confidence catches are likely very accurate
3. **Conservative Approach**: The heuristics are appropriately cautious

## Weaknesses

1. **Low Recall**: Missing 83.36% of OTPs according to ground truth labels
2. **Strict Requirements**: Requires explicit OTP keywords/phrases to trigger
3. **Missing Patterns**: Many legitimate OTP formats not covered

## Pattern Analysis of Missed OTPs

Based on analysis of 494 actual missed OTPs (excluding NOT_OTP labeled messages):

1. **No numeric code (72.5%)**: 358 missed OTPs have no numeric code pattern
   - These legitimately need ML classification
   - Examples: Error messages, delivery notifications without codes

2. **Has code but no keywords (27.5%)**: 136 have codes but lack OTP keywords/phrases
   - These could potentially be caught with improved patterns
   - Examples: Codes at start without "OTP" or "code" keywords

3. **Code length distribution**:
   - 4-digit codes: 128 (25.9%)
   - 5-digit codes: 5 (1.0%)
   - 6-digit codes: 3 (0.6%)

4. **Pattern indicators**:
   - Has OTP keyword: 34 (6.9%) - but still missed!
   - Has OTP phrases: 15 (3.0%)
   - Has validity period: 25 (5.1%)
   - Security warnings: 4 (0.8%)

## Recommendations

### Immediate Actions

1. **Review Ground Truth Labels**
   - Many messages with `is_otp=True` have `intent='NOT_OTP'`
   - These should be marked as `is_otp=False`
   - This is causing inflated false negative counts

2. **Investigate Why OTP Keywords Are Missed**
   - 34 messages have OTP keywords but weren't caught
   - Review keyword matching logic (case sensitivity, word boundaries)

### Heuristic Improvements

#### 1. Expand Code-at-Start Pattern
**Current**: Not specifically handled
**Recommendation**: Add pattern for codes at message start
```python
# Pattern: Code at start followed by OTP context
re.compile(r"^\b\d{4,8}\b\s*(?:is|for|your|use|enter|verification|code)", re.IGNORECASE)
```

#### 2. Improve Keyword Matching
**Current**: Basic substring matching
**Recommendation**: 
- Use word boundaries: `\bOTP\b` instead of `"otp" in text`
- Ensure case-insensitive matching
- Verify keyword list completeness

#### 3. Add Validity Period Indicator
**Current**: Not used as indicator
**Recommendation**: If message contains validity words + numeric code → boost confidence
```python
validity_words = ["valid", "validity", "expires", "expiry", "minutes", "min", "seconds"]
if any(word in text_lower for word in validity_words) and has_code:
    confidence = max(confidence, 0.70)
```

#### 4. Add Security Warning Indicator
**Current**: Not used as indicator
**Recommendation**: Security warnings + code → likely OTP
```python
security_warnings = ["do not share", "don't share", "keep secret", "confidential", 
                     "never share", "do not disclose"]
if any(warning in text_lower for warning in security_warnings) and has_code:
    confidence = max(confidence, 0.75)
```

#### 5. Expand Verification Word Patterns
**Current**: Limited verification words
**Recommendation**: Expand and add pattern matching
```python
verification_patterns = [
    re.compile(r"(?:verify|verification|authenticate|login).*?\b\d{4,8}\b", re.IGNORECASE),
    re.compile(r"\b\d{4,8}\b.*?(?:verify|verification|authenticate|login)", re.IGNORECASE)
]
```

#### 6. Lower Short Message Threshold
**Current**: Messages < 150 chars get 0.60 confidence
**Recommendation**: Consider 100 chars as threshold, or add length-based confidence scaling

#### 7. Improve Code Detection
**Current**: `\b\d{4,8}\b` pattern
**Recommendation**: 
- Ensure it doesn't match dates, amounts, phone numbers
- Add context checks (not part of transaction amounts)
- Consider isolated codes (surrounded by non-numeric chars)

### Example Improved Patterns

```python
# Code at start with OTP context
START_CODE_PATTERN = re.compile(
    r"^\b\d{4,8}\b\s*(?:is|for|your|use|enter|verification|code|otp|password)",
    re.IGNORECASE
)

# Verification words with code
VERIFICATION_CODE_PATTERN = re.compile(
    r"(?:verify|verification|authenticate|login|sign.?in).*?\b\d{4,8}\b",
    re.IGNORECASE
)

# Security warning with code
SECURITY_CODE_PATTERN = re.compile(
    r"(?:do\s+not\s+share|don'?t\s+share|keep\s+secret|confidential|never\s+share).*?\b\d{4,8}\b",
    re.IGNORECASE
)
```

## Expected Impact

After implementing improvements:
- **Recall**: Could improve from 16.64% to 40-50% (estimating 2-3x improvement)
- **Precision**: Should remain near 100% (may drop slightly to ~98-99%)
- **High confidence catches**: Should increase from 4.22% to 8-12%

## Conclusion

The heuristic classifier is working as designed - it's conservative and precise. To improve recall while maintaining precision:

1. **Fix ground truth labels** (critical for accurate evaluation)
2. **Implement pattern improvements** listed above
3. **Investigate why existing keywords are being missed**
4. **Use ML for messages without clear patterns** (this is expected and appropriate)

The hybrid approach (heuristics + ML) is correct - heuristics catch obvious OTPs quickly, ML handles ambiguous cases. The current 16.64% catch rate for clear cases is reasonable, but improvements could push it to 25-40% without sacrificing precision.
