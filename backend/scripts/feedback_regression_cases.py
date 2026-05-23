"""Sanitized regression cases for SMS classifier feedback follow-up.

These cases are intentionally small and focused on the recent false-positive
work:
- bank/card transaction alerts must stay NOT_OTP
- legitimate branded OTPs must stay OTP and not phishing
- delivery/service OTPs must stay OTP and not phishing
- legitimate branded informational/payment/bill/order links must not be
  phishing
- a few synthetic phishing cases must remain phishing
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class FeedbackRegressionCase:
    case_id: str
    sender: str
    text: str
    expected_is_otp: bool
    expected_is_phishing: bool
    expected_otp_intent: Optional[str] = None
    category: str = ""


FEEDBACK_REGRESSION_CASES: List[FeedbackRegressionCase] = [
    FeedbackRegressionCase(
        case_id="bank_card_txn_01",
        sender="HDFCBK",
        text=(
            "Rs. 4,820 spent on your HDFC card ending XX42 at ABC MART. "
            "Available limit is now Rs. 1,20,000."
        ),
        expected_is_otp=False,
        expected_is_phishing=False,
        category="bank_card_alert",
    ),
    FeedbackRegressionCase(
        case_id="bank_card_txn_02",
        sender="ICICIB",
        text=(
            "Your ICICI debit card was used for INR 2,980 at FASTFOOD. "
            "If this was not you, contact the bank."
        ),
        expected_is_otp=False,
        expected_is_phishing=False,
        category="bank_card_alert",
    ),
    FeedbackRegressionCase(
        case_id="bank_upi_txn_icici_feedback",
        sender="AD-ICICIT-S",
        text=(
            "ICICI Bank Acct XX123 debited for Rs 360.00 on 23-May-26; "
            "UPI: 123456789012. Avl Bal Rs 1,000. If this was not you, "
            "call the bank or SMS BLOCK."
        ),
        expected_is_otp=False,
        expected_is_phishing=False,
        category="bank_upi_alert",
    ),
    FeedbackRegressionCase(
        case_id="otp_decathlon_login",
        sender="DECATHLON",
        text=(
            "624381 is your Decathlon login OTP. Valid for 10 minutes. "
            "Do not share this code."
        ),
        expected_is_otp=True,
        expected_is_phishing=False,
        category="legit_otp",
    ),
    FeedbackRegressionCase(
        case_id="otp_snapchat_signin",
        sender="SNAPCHAT",
        text=(
            "Your Snapchat verification code is 731904. Use it to sign in."
        ),
        expected_is_otp=True,
        expected_is_phishing=False,
        category="legit_otp",
    ),
    FeedbackRegressionCase(
        case_id="otp_indmoney_login",
        sender="INDMONEY",
        text=(
            "Use 846201 to verify your INDmoney login. Never share this code."
        ),
        expected_is_otp=True,
        expected_is_phishing=False,
        category="legit_otp",
    ),
    FeedbackRegressionCase(
        case_id="otp_jiohotstar_signin",
        sender="JIHOTSTAR",
        text=(
            "559201 is your JioHotstar verification code for sign in."
        ),
        expected_is_otp=True,
        expected_is_phishing=False,
        category="legit_otp",
    ),
    FeedbackRegressionCase(
        case_id="otp_whatsapp_phone_change",
        sender="WHATSAPP",
        text=(
            "Your WhatsApp code is 482917. Do not share this code with anyone. "
            "Use it to verify your new phone number."
        ),
        expected_is_otp=True,
        expected_is_phishing=False,
        expected_otp_intent="APP_ACCOUNT_CHANGE_OTP",
        category="legit_otp",
    ),
    FeedbackRegressionCase(
        case_id="otp_delivery_code_01",
        sender="DELHIVRY",
        text=(
            "Delivery code 482917 for your parcel from Delhivery. Share it "
            "with the courier only after checking the package."
        ),
        expected_is_otp=True,
        expected_is_phishing=False,
        expected_otp_intent="DELIVERY_OR_SERVICE_OTP",
        category="delivery_service_otp",
    ),
    FeedbackRegressionCase(
        case_id="otp_service_guest_code",
        sender="BLUEDART",
        text=(
            "Guest code 660842 for building entry at Blue Dart. Please share "
            "the code at the gate."
        ),
        expected_is_otp=True,
        expected_is_phishing=False,
        expected_otp_intent="DELIVERY_OR_SERVICE_OTP",
        category="delivery_service_otp",
    ),
    FeedbackRegressionCase(
        case_id="brand_order_link",
        sender="AMAZON",
        text=(
            "Your Amazon order has shipped. Track it here: "
            "https://amazon.example/track/AB12CD"
        ),
        expected_is_otp=False,
        expected_is_phishing=False,
        category="legit_brand_link",
    ),
    FeedbackRegressionCase(
        case_id="brand_bill_link",
        sender="FLIPKART",
        text=(
            "Your Flipkart bill is ready. View the statement in the app or "
            "at https://flipkart.example/pay/BILL"
        ),
        expected_is_otp=False,
        expected_is_phishing=False,
        category="legit_brand_link",
    ),
    FeedbackRegressionCase(
        case_id="brand_payment_link",
        sender="PAYTM",
        text=(
            "Payment of Rs. 349 was successful. View your receipt here: "
            "https://paytm.example/receipt/AB12"
        ),
        expected_is_otp=False,
        expected_is_phishing=False,
        category="legit_brand_link",
    ),
    FeedbackRegressionCase(
        case_id="phish_bank_login_link",
        sender="HDFCBK",
        text=(
            "Urgent: Your HDFC account will be blocked today. Verify now at "
            "http://hdfc-secure-example.ru/login and enter code 482917."
        ),
        expected_is_otp=False,
        expected_is_phishing=True,
        category="synthetic_phishing",
    ),
    FeedbackRegressionCase(
        case_id="phish_redelivery_fee",
        sender="COURIER",
        text=(
            "Your parcel is on hold. Pay a redelivery fee at "
            "https://bit.ly/redeliver-now to release it."
        ),
        expected_is_otp=False,
        expected_is_phishing=True,
        category="synthetic_phishing",
    ),
    FeedbackRegressionCase(
        case_id="phish_brand_redelivery_fee",
        sender="BLUEDART",
        text=(
            "Your parcel is on hold. Pay Rs 29 redelivery fee at "
            "https://bit.ly/bluedart-redeliver to release shipment."
        ),
        expected_is_otp=False,
        expected_is_phishing=True,
        category="synthetic_phishing",
    ),
    FeedbackRegressionCase(
        case_id="phish_upi_refund_link",
        sender="UPIALERT",
        text=(
            "Your UPI refund is pending. Claim your refund at "
            "https://bit.ly/upi-refund and verify payment now."
        ),
        expected_is_otp=False,
        expected_is_phishing=True,
        category="synthetic_phishing",
    ),
    FeedbackRegressionCase(
        case_id="phish_prize_claim",
        sender="REWARD",
        text=(
            "Congratulations! Claim your cashback reward immediately at "
            "https://tinyurl.example/claim before it expires."
        ),
        expected_is_otp=False,
        expected_is_phishing=True,
        category="synthetic_phishing",
    ),
    FeedbackRegressionCase(
        case_id="phish_fake_security_code",
        sender="SECURITY",
        text=(
            "Your verification code is 915204. If you did not request this, "
            "open https://secure-check.example and re-enter your details."
        ),
        expected_is_otp=True,
        expected_is_phishing=True,
        category="synthetic_phishing",
    ),
]
