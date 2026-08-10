# Owner Validation Snapshot

The owner explicitly asked for one live creative experiment that makes OTP-fraud protection clear, with unattended testing and launch authority.

## Confirmed direction

- Market: India; language and voice: natural Indian English.
- Promise: help protect against OTP fraud by showing what a code appears to authorize before it is shared.
- Proof: deterministic account-change SMS and the app's visible `For Account change` / `Never share this code` state.
- Claim boundary: the app analyzes the SMS; it does not listen to calls, identify every fraud attempt, or guarantee prevention.
- Test design: keep campaign controls fixed and change only the explicitness of the OTP-fraud problem statement.

## Production decision

Proceed with a single challenger concept across Google App image ratios and one vertical product-proof video. Judge downstream user quality on distinct `default_sms_set`, `first_sms_classified`, trial starts, and verified paid conversions—not clicks alone.
