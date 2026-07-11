from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.classification.phishing_policy import (
    _apply_phishing_policy,
    _detect_legit_low_risk_context,
)


class PhishingPolicyTest(unittest.TestCase):
    def test_first_party_receipt_is_downgraded(self) -> None:
        is_phishing, score, reasons = _apply_phishing_policy(
            text="Your order is completed. View your receipt at https://amazon.in/orders/12345",
            sender="Amazon",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.91,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertFalse(is_phishing)
        self.assertLess(score, 0.5)
        self.assertTrue(
            any(
                label in reason
                for reason in reasons
                for label in (
                    "bank transaction / standing-instruction notice",
                    "receipt / e-bill",
                    "completed / confirmed order",
                )
            )
        )

    def test_first_party_alignment_lowers_receipt_cap(self) -> None:
        aligned = _detect_legit_low_risk_context(
            text="Your order is completed. View your receipt at https://amazon.in/orders/12345",
            sender="Amazon",
            is_otp=False,
            otp_intent="NOT_OTP",
        )
        neutral = _detect_legit_low_risk_context(
            text="Your order is completed. View your receipt at https://billing.example.com/orders/12345",
            sender="Amazon",
            is_otp=False,
            otp_intent="NOT_OTP",
        )

        self.assertIsNotNone(aligned)
        self.assertIsNotNone(neutral)
        self.assertLess(aligned["cap"], 0.5)
        self.assertLess(aligned["cap"], neutral["cap"])

    def test_service_appointment_is_downgraded(self) -> None:
        is_phishing, score, reasons = _apply_phishing_policy(
            text="Your service appointment is confirmed for tomorrow. Manage it at https://urbancompany.com/bookings/9981",
            sender="UrbanCompany",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.78,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertFalse(is_phishing)
        self.assertLess(score, 0.5)
        self.assertTrue(any("booked / completed service appointment" in reason for reason in reasons))

    def test_telecom_notice_is_downgraded(self) -> None:
        is_phishing, score, reasons = _apply_phishing_policy(
            text="Your prepaid plan is active. Data usage alert: 80% used. Manage at https://jio.com/account",
            sender="Jio",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.82,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertFalse(is_phishing)
        self.assertLess(score, 0.5)
        self.assertTrue(
            any(
                "bill / data alert" in reason or "telecom plan / data / account notice" in reason
                for reason in reasons
            )
        )

    def test_delivery_service_otp_sharing_is_downgraded(self) -> None:
        is_phishing, score, reasons = _apply_phishing_policy(
            text="Please share this delivery code after checking the package. Track it at https://swiggy.com/delivery/1234",
            sender="Swiggy",
            is_otp=True,
            otp_intent="DELIVERY_OR_SERVICE_OTP",
            raw_phish_prob=0.73,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertFalse(is_phishing)
        self.assertLess(score, 0.5)
        self.assertTrue(
            any(
                "app OTP verification" in reason
                or "delivery / order confirmation" in reason
                or "delivery / service OTP sharing" in reason
                for reason in reasons
            )
        )

    def test_plain_share_otp_is_allowed_only_for_delivery_intent(self) -> None:
        safe, _, _ = _apply_phishing_policy(
            text="Share OTP 482917 with the delivery agent after checking the parcel.",
            sender="Delhivery",
            is_otp=True,
            otp_intent="DELIVERY_OR_SERVICE_OTP",
            raw_phish_prob=0.82,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )
        unsafe, _, _ = _apply_phishing_policy(
            text="Share OTP 482917 with the caller to restore your account.",
            sender="Delhivery",
            is_otp=True,
            otp_intent="APP_LOGIN_OTP",
            raw_phish_prob=0.82,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertFalse(safe)
        self.assertTrue(unsafe)

    def test_link_bearing_order_notice_requires_first_party_domain(self) -> None:
        is_phishing, score, _ = _apply_phishing_policy(
            text="Your Amazon order is completed. View details at https://orders-example.net/1234",
            sender="Amazon",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.88,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertTrue(is_phishing)
        self.assertGreaterEqual(score, 0.5)

    def test_short_brand_token_does_not_match_hostname_substring(self) -> None:
        context = _detect_legit_low_risk_context(
            text="Your Vi plan is active. View it at https://evil.example/account",
            sender="Vi",
            is_otp=False,
            otp_intent="NOT_OTP",
        )

        self.assertIsNone(context)

    def test_lookalike_payment_link_stays_phishing(self) -> None:
        is_phishing, score, reasons = _apply_phishing_policy(
            text="Your Swiggy order is ready. Pay now to complete delivery: https://swiggy-support.co/pay/1234",
            sender="Swiggy",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.88,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertTrue(is_phishing)
        self.assertGreaterEqual(score, 0.5)
        self.assertTrue(any("payment trap with link" in reason for reason in reasons))

    def test_kyc_account_block_override_stays_phishing(self) -> None:
        is_phishing, score, reasons = _apply_phishing_policy(
            text="KYC incomplete. Verify now to unblock your SBI account: https://secure-update.co/login",
            sender="SBI",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.84,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertTrue(is_phishing)
        self.assertGreaterEqual(score, 0.5)
        self.assertTrue(any("KYC / account-blocked urgency" in reason for reason in reasons))
        self.assertTrue(any("brand-domain mismatch" in reason for reason in reasons))

    def test_danger_signal_does_not_promote_ml_negative(self) -> None:
        is_phishing, score, reasons = _apply_phishing_policy(
            text="KYC incomplete. Verify now at https://secure-update.co/login",
            sender="SBI",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.31,
            is_phishing_ml=False,
            phish_threshold=0.5,
        )

        self.assertFalse(is_phishing)
        self.assertEqual(score, 0.31)
        self.assertTrue(any("below ML threshold" in reason for reason in reasons))

    def test_numeric_sender_kyc_login_lure_promotes_ml_negative(self) -> None:
        is_phishing, score, reasons = _apply_phishing_policy(
            text="Complete your KYC today. Log in to your payment account to continue.",
            sender="57575711",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.33,
            is_phishing_ml=False,
            phish_threshold=0.5,
        )

        self.assertTrue(is_phishing)
        self.assertEqual(score, 0.5)
        self.assertTrue(any("numeric-sender KYC login lure" in reason for reason in reasons))

    def test_sender_alignment_alone_does_not_allowlist(self) -> None:
        is_phishing, score, reasons = _apply_phishing_policy(
            text="Pay now at https://swiggy.com/pay/complete",
            sender="Swiggy",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.81,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertTrue(is_phishing)
        self.assertGreaterEqual(score, 0.5)
        self.assertTrue(any("payment trap with link" in reason for reason in reasons))

    def test_brand_sales_quote_follow_up_is_downgraded(self) -> None:
        is_phishing, score, _ = _apply_phishing_policy(
            text="Further to your interest in MG_COMET_EV, your advisor sent a detailed quote.",
            sender="CP-MGINET-T",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.71,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertFalse(is_phishing)
        self.assertLess(score, 0.5)

    def test_registered_airline_checkin_with_redacted_link_is_downgraded(self) -> None:
        is_phishing, score, _ = _apply_phishing_policy(
            text="Please visit <URL:abc123> to complete your web check-in. Thank you - Air India Express",
            sender="AD-FLYAIX-S",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.66,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertFalse(is_phishing)
        self.assertLess(score, 0.5)

    def test_unknown_sender_airline_checkin_link_stays_phishing(self) -> None:
        is_phishing, score, _ = _apply_phishing_policy(
            text="Please visit <URL:abc123> to complete your web check-in. Thank you - Air India Express",
            sender="UNKNOWN",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.66,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertTrue(is_phishing)
        self.assertGreaterEqual(score, 0.5)

    def test_registered_service_feedback_is_downgraded(self) -> None:
        is_phishing, score, _ = _apply_phishing_policy(
            text="Please tell us about your Insta Help experience. Click here: <URL:abc123> - Urban Company",
            sender="CP-URBNCP-S",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.98,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertFalse(is_phishing)
        self.assertLess(score, 0.5)

    def test_registered_bill_copy_notice_is_downgraded(self) -> None:
        is_phishing, score, _ = _apply_phishing_policy(
            text="Download your 1 Month Vi bill copy on Vi App at <URL:abc123>",
            sender="VX-ViCARE-S",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.96,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertFalse(is_phishing)
        self.assertLess(score, 0.5)

    def test_registered_restaurant_ebill_is_downgraded(self) -> None:
        is_phishing, score, _ = _apply_phishing_policy(
            text="Thanks for your McDonald's order eBill: <URL:abc123>. Review us.",
            sender="VA-McDnld-S",
            is_otp=False,
            otp_intent="NOT_OTP",
            raw_phish_prob=0.91,
            is_phishing_ml=True,
            phish_threshold=0.5,
        )

        self.assertFalse(is_phishing)
        self.assertLess(score, 0.5)


if __name__ == "__main__":
    unittest.main()
