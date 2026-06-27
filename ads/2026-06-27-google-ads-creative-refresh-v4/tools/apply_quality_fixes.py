from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont


CENTRAL = Path(r"D:\Projects\ad creatives")
RUN = Path(r"D:\Projects\SMS datasets and project\ads\2026-06-27-google-ads-creative-quality-refresh-v2")

sys.path.insert(0, str(CENTRAL))
from adengine.brandkit import load_brand_kit  # noqa: E402
from adengine.compositor import render  # noqa: E402


PRIZE_HOOK_OLD = "Prize SMS says you won. App shows bank risk."
PRIZE_HOOK_MID = "Bank details in a prize SMS. App flags the risk."
PRIZE_HOOK_NEW = "Bank details in a prize SMS. App warns before you tap."
OTP_INBOX_OLD = "Bank login SMS is buried. App finds the OTP."
OTP_INBOX_MID = "Bank OTP is buried. App shows the code."
OTP_INBOX_CURRENT = "Bank OTP SMS is buried. App shows the code."
OTP_INBOX_NEW = "Bank OTP SMS is buried. App shows it with less stress."
VIDEO_FINAL_OLD = "Review the text before sharing details."
VIDEO_FINAL_NEW = "App shows the warning before bank details."


def load_yaml(rel: str) -> dict:
    path = RUN / rel
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def dump_yaml(rel: str, data: dict) -> None:
    (RUN / rel).write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False, width=110), encoding="utf-8")


def load_json(rel: str):
    return json.loads((RUN / rel).read_text(encoding="utf-8"))


def dump_json(rel: str, data) -> None:
    (RUN / rel).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def font(size: int):
    path = Path("C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def replace_text(value):
    if isinstance(value, str):
        return (
            value.replace(PRIZE_HOOK_OLD, PRIZE_HOOK_NEW)
            .replace(PRIZE_HOOK_MID, PRIZE_HOOK_NEW)
            .replace(OTP_INBOX_OLD, OTP_INBOX_NEW)
            .replace(OTP_INBOX_MID, OTP_INBOX_NEW)
            .replace(OTP_INBOX_CURRENT, OTP_INBOX_NEW)
            .replace(VIDEO_FINAL_OLD, VIDEO_FINAL_NEW)
        )
    if isinstance(value, list):
        return [replace_text(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_text(item) for key, item in value.items()}
    return value


def patch_core_copy() -> None:
    for rel in [
        "hooks.yaml",
        "message_map.yaml",
        "storyboard.yaml",
        "slideshow_scam_prize_9x16.json",
        "video_prompts.json",
        "image_prompts.json",
        "hierarchy_specs.yaml",
        "proof_specs.yaml",
    ]:
        path = RUN / rel
        if not path.exists():
            continue
        if path.suffix == ".json":
            dump_json(rel, replace_text(load_json(rel)))
        else:
            dump_yaml(rel, replace_text(load_yaml(rel)))

    slideshow = load_json("slideshow_scam_prize_9x16.json")
    for frame in slideshow.get("frames", []):
        frame["bbox_pct"] = {"x": 14, "y": 33, "w": 72, "h": 55}
    dump_json("slideshow_scam_prize_9x16.json", slideshow)

    message_map = load_yaml("message_map.yaml")
    for message in message_map.get("messages", []):
        if message.get("hook_id") == "H_OTP_INBOX":
            message["emotional_payoff"] = "Less stress when a bank login OTP is needed quickly."
            message["headline_tests"] = [{"id": "short_otp", "on_image_headline": "Bank OTPs are easier to find."}]
        if message.get("hook_id") == "H_SCAM_PRIZE":
            message["headline_tests"] = [{"id": "short_prize", "on_image_headline": "Prize SMS asks for bank details."}]
    dump_yaml("message_map.yaml", message_map)

    proof_specs = load_yaml("proof_specs.yaml")
    for proof in proof_specs.get("proofs", []):
        for check in proof.get("contrast_checks", []):
            if str(check.get("bg", "")).lower() == "#169b62":
                check["bg"] = "#0F6F45"
    dump_yaml("proof_specs.yaml", proof_specs)

    for rel in ["video_scripts.md", "storyboards.md", "copy_pack.md", "creative_strategy.md", "CREATIVE_CRITIQUE_FIXES.md"]:
        path = RUN / rel
        if path.exists():
            path.write_text(replace_text(path.read_text(encoding="utf-8")), encoding="utf-8")

    vo = RUN / "voiceover_scripts.csv"
    if vo.exists():
        rows = list(csv.DictReader(vo.open("r", encoding="utf-8-sig", newline="")))
        fields = rows[0].keys() if rows else ["asset_id", "language", "voice", "speed", "script"]
        for row in rows:
            row["script"] = (
                "A prize-style text can push you toward bank details. SMS Classifier keeps the warning "
                "reason visible before you tap, so you get a calmer moment to review first."
            )
        with vo.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fields))
            writer.writeheader()
            writer.writerows(rows)


def patch_static_assets() -> None:
    layouts = replace_text(load_json("layout_specs.json"))
    for layout in layouts:
        asset_id = str(layout.get("asset_id", ""))
        for element in layout.get("elements", []):
            if element.get("type") == "logo":
                element["bbox_pct"] = {"x": 6, "y": 6, "w": 40, "h": 8}
            elif element.get("type") == "product_ui":
                if asset_id == "IMG_OTP_ACCOUNT_LANDSCAPE":
                    element["bbox_pct"] = {"x": 46, "y": 5, "w": 52, "h": 90}
                elif "LANDSCAPE" in asset_id:
                    element["bbox_pct"] = {"x": 50, "y": 8, "w": 48, "h": 84}
                elif "PORTRAIT" in asset_id and "OTP_ACCOUNT" in asset_id:
                    element["bbox_pct"] = {"x": 10, "y": 16, "w": 80, "h": 52}
                elif "PORTRAIT" in asset_id and "OTP_INBOX" in asset_id:
                    element["bbox_pct"] = {"x": 12, "y": 34, "w": 76, "h": 54}
                elif asset_id == "IMG_SCAM_PRIZE_PORTRAIT":
                    element["bbox_pct"] = {"x": 7, "y": 34, "w": 86, "h": 58}
                elif "PORTRAIT" in asset_id:
                    element["bbox_pct"] = {"x": 10, "y": 35, "w": 80, "h": 52}
                elif "SQUARE" in asset_id and "OTP_ACCOUNT" in asset_id:
                    element["bbox_pct"] = {"x": 14, "y": 16, "w": 72, "h": 56}
                else:
                    element["bbox_pct"] = {"x": 12, "y": 36, "w": 76, "h": 54}
            elif element.get("type") == "headline":
                if asset_id == "IMG_OTP_ACCOUNT_LANDSCAPE":
                    element["bbox_pct"] = {"x": 5, "y": 24, "w": 38, "h": 34}
                elif "LANDSCAPE" in asset_id:
                    element["bbox_pct"] = {"x": 5, "y": 24, "w": 40, "h": 34}
                elif "PORTRAIT" in asset_id and "OTP_INBOX" in asset_id:
                    element["bbox_pct"] = {"x": 7, "y": 15, "w": 82, "h": 15}
                elif "SQUARE" in asset_id and "OTP_ACCOUNT" in asset_id:
                    element["bbox_pct"] = {"x": 9, "y": 75, "w": 82, "h": 16}
    dump_json("layout_specs.json", layouts)

    matrix = RUN / "creative_matrix.csv"
    rows = list(csv.DictReader(matrix.open("r", encoding="utf-8-sig", newline="")))
    fields = rows[0].keys() if rows else []
    for row in rows:
        for key in row:
            row[key] = replace_text(row[key])
        if row.get("asset_id") == "VID_SCAM_PRIZE_9x16":
            row["spec"] = "google_app_campaign_video"
    with matrix.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        writer.writerows(rows)

    brand = load_brand_kit(RUN)
    for layout in layouts:
        image = render(layout, brand, background=layout.get("custom_background"))
        out = RUN / "assets" / f"{layout['asset_id']}_{layout['spec']}.png"
        image.save(out)
        image.save(RUN / "exports" / out.name)

    copy_rows = []
    for row in rows:
        if row.get("format") == "image":
            copy_rows.append(
                {
                    "asset_id": row["asset_id"],
                    "headline": row["headline"][:30],
                    "long_headline": row["primary_text"][:90],
                    "description": row["description"][:90],
                    "cta": "Start 14-day trial",
                }
            )
    with (RUN / "copy_pack.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["asset_id", "headline", "long_headline", "description", "cta"])
        writer.writeheader()
        writer.writerows(copy_rows)
    (RUN / "copy_pack.md").write_text(
        "# Text Asset Pack\n\n"
        + "\n".join(
            f"- {row['asset_id']}: {row['headline']} | {row['description']} | CTA: {row['cta']}"
            for row in copy_rows
        )
        + "\n",
        encoding="utf-8",
    )


def shared_negatives() -> list[str]:
    return [
        "google messages",
        "messages for web",
        "samsung messages",
        "messenger",
        "facebook",
        "whatsapp",
        "telegram",
        "instagram",
        "bulk sms",
        "sms gateway",
        "sms marketing",
        "sms api",
        "otp api",
        "otp service",
        "email",
        "call blocker",
        "truecaller",
        "authenticator",
        "2fa",
        "totp",
        "loan",
        "jobs",
        "career",
        "course",
        "ios",
        "iphone",
        "pc",
        "windows",
        "web",
        "apk",
        "mod apk",
        "free sms",
        "fake sms",
        "meaning",
        "definition",
        "examples",
    ]


def h(text: str, role: str | None = None) -> dict:
    item = {"text": text}
    if role:
        item["role"] = role
    return item


def rsa(rsa_id: str, headlines: list[dict], descriptions: list[str]) -> dict:
    return {
        "id": rsa_id,
        "headlines": headlines,
        "descriptions": descriptions,
        "paths": {"path1": "sms-app", "path2": "review"},
        "sitelinks": [
            {"text": "OTP Inbox", "description1": "Find codes faster", "description2": "Review service SMS"},
            {"text": "Suspicious SMS", "description1": "See marked texts", "description2": "Pause before tapping"},
            {"text": "Pro Trial", "description1": "Try Pro features", "description2": "INR 199/year after"},
            {"text": "Privacy Controls", "description1": "Review settings", "description2": "See data choices"},
        ],
        "callouts": ["14-day trial", "INR 199/year Pro", "OTP inbox", "Scam-aware sorting", "Default SMS app"],
        "structured_snippets": [{"header": "Types", "values": ["OTP", "Service SMS", "Suspicious links", "Bank alerts"]}],
        "business_name": "SMS Classifier",
    }


COMMON_DESCRIPTIONS = [
    "The app shows codes, service alerts, and review-needed texts in one calm view.",
    "The app flags odd links and bank-detail requests while trial terms stay clear.",
    "The app organizes login messages and service updates for faster review.",
    "The app finds recent codes and shows review labels before you reply.",
]


def cluster(
    cid: str,
    persona_id: str,
    search_moment: str,
    primary_query: str,
    keywords: list[str],
    category_terms: list[str],
    primary_promise: str,
    claim_boundary: str,
    estimated_monthly_searches: int,
    priority,
    h1: str,
    proof: list[str],
) -> dict:
    return {
        "id": cid,
        "persona_id": persona_id,
        "search_moment": search_moment,
        "primary_query": primary_query,
        "keywords": keywords,
        "category_terms": category_terms,
        "primary_promise": primary_promise,
        "claim_boundary": claim_boundary,
        "estimated_monthly_searches": estimated_monthly_searches,
        "priority": priority,
        "negative_keywords": shared_negatives(),
        "landing_page_h1": h1,
        "landing_page_proof": proof,
    }


def search_groups() -> list[dict]:
    groups = [
        cluster(
            "sms_app_category_scale",
            "otp_searcher",
            "category_scale",
            "messages app",
            [
                "messages app",
                "sms app",
                "sms message app",
                "text message app",
                "default sms app",
                "best messaging app for android",
                "messaging apps for android",
            ],
            ["messages app", "SMS app", "Android SMS app"],
            "Android SMS app keeps OTPs, service texts, and review-needed messages easier to scan.",
            "Organization and review help only; no fraud-prevention promise.",
            37790,
            1,
            "Messages App For Android",
            ["OTP inbox and review-needed messages in one Android SMS app.", "Organization and review proof only."],
        ),
        cluster(
            "spam_sms_problem_scale",
            "family_helper",
            "problem_aware_scale",
            "i keep getting spam texts",
            ["i keep getting spam texts", "spam messages", "spam text messages", "spam sms", "spam sms messages", "sms filter"],
            ["spam SMS app", "SMS filter", "Android SMS app"],
            "SMS app flags spam-looking texts so users can review before replying.",
            "Flags and review labels only; no blocking promise.",
            26720,
            2,
            "Spam SMS Review App",
            ["Review spam-looking SMS in a calmer default inbox.", "Bounded review labels only."],
        ),
        cluster(
            "scam_text_problem_scale",
            "otp_fraud_worrier",
            "problem_aware_scale",
            "scam text messages",
            [
                "scam text messages",
                "text scams",
                "smishing",
                "phishing scam text",
                "phishing text messages",
                "phishing texts",
                "sms scam",
                "phishing sms",
                "sms fraud",
            ],
            ["scam text app", "SMS warning app", "phishing SMS", "Android SMS app"],
            "SMS app warns before suspicious-looking links or details requests are acted on.",
            "Shows warnings and review context; no safe-or-unsafe certification.",
            23430,
            3,
            "Scam Text Message Review",
            ["SMS warning UI for suspicious-looking links and details requests.", "Bounded review context."],
        ),
        cluster(
            "otp_utility_risk_scale",
            "otp_fraud_worrier",
            "otp_utility_and_risk",
            "otp app",
            [
                "otp app",
                "otp scam",
                "otp sms",
                "bank otp",
                "otp fraud",
                "delivery otp scam",
                "otp scam warning app",
                "otp fraud warning app",
            ],
            ["OTP app", "SMS app", "OTP warning app", "Android SMS app"],
            "SMS app shows OTP context and helps users find bank codes faster.",
            "OTP context and organization only; no fraud-prevention promise.",
            3450,
            4,
            "OTP App For SMS Codes",
            ["OTP inbox and review warning screens.", "Bounded OTP-context claim."],
        ),
        cluster(
            "sms_organizer_control",
            "busy_otp_user",
            "solution_aware_control",
            "sms organizer",
            ["sms organizer", "sms organizer app", "sms organiser app", "default sms app"],
            ["SMS organizer", "SMS app", "Android SMS app"],
            "SMS app keeps OTPs and service messages easier to scan.",
            "Organization and review help only; no perfect-sorting promise.",
            1410,
            5,
            "SMS Organizer",
            ["OTP and service code organization in SMS Classifier.", "Bounded organization claim only."],
        ),
        cluster(
            "sms_classifier_brand_exact",
            "brand_searcher",
            "brand_exact_defensive",
            "sms classifier",
            ["sms classifier", "sms classifier app"],
            ["SMS Classifier app", "Android SMS app"],
            "SMS Classifier app listing for OTP organization and SMS review.",
            "Brand navigation only; no unbounded safety claim.",
            0,
            "defensive_brand",
            "SMS Classifier App",
            ["App listing and trial terms.", "Brand coverage is exact/phrase only."],
        ),
        cluster(
            "sms_permissions_trust_holdout",
            "privacy_cautious_user",
            "trust_objection_holdout",
            "sms permissions android",
            ["sms permissions android", "default sms permissions", "sms app privacy", "sms app data privacy"],
            ["SMS privacy", "Android SMS app", "default SMS app"],
            "SMS app shows permissions and feature controls clearly before Pro.",
            "Explain settings honestly; no absolute privacy claim.",
            0,
            "defensive_trust",
            "SMS App Privacy",
            ["Privacy and settings screens explain review feature controls.", "No absolute privacy claim."],
        ),
    ]
    return groups


def search_rsas() -> dict[str, list[dict]]:
    return {
        "sms_app_category_scale": [
            rsa(
                "messages_app_control",
                [
                    h("Messages App Android", "query_echo"),
                    h("Inbox Finds Bank Codes"),
                    h("SMS App For OTPs"),
                    h("Bank Code Access"),
                    h("Shows Review Labels"),
                    h("Service Alerts Grouped"),
                    h("Simple Text Helper"),
                    h("Calmer Code View"),
                    h("Scam Link Warnings"),
                    h("Built For India SMS"),
                    h("Family SMS Review"),
                ],
                COMMON_DESCRIPTIONS,
            ),
            rsa(
                "messages_app_challenger",
                [
                    h("SMS Message App", "query_echo"),
                    h("Text Message App"),
                    h("SMS App Sorts Codes"),
                    h("App Shows Odd Links"),
                    h("OTP And Alerts Together"),
                    h("Bank Alerts In View"),
                    h("Service SMS Sorted"),
                    h("Review Links First"),
                    h("Price Terms Visible"),
                    h("Install Listing Ready"),
                    h("Daily Texts Organized"),
                ],
                COMMON_DESCRIPTIONS,
            ),
        ],
        "spam_sms_problem_scale": [
            rsa(
                "spam_sms_control",
                [
                    h("Spam Messages Keep Coming", "query_echo"),
                    h("SMS Filter For Texts"),
                    h("Spam SMS App Review"),
                    h("Flags Spam-Looking SMS"),
                    h("App Flags Odd Links"),
                    h("Review Texts Before Reply"),
                    h("Bank Requests In View"),
                    h("Service Alerts In View"),
                    h("OTP Inbox Included"),
                    h("INR 199 After Trial"),
                    h("Default Text Helper"),
                ],
                COMMON_DESCRIPTIONS,
            ),
            rsa(
                "spam_sms_challenger",
                [
                    h("Spam SMS Messages", "query_echo"),
                    h("SMS Filter Inbox"),
                    h("App Spots Reply Traps"),
                    h("Review Odd Messages"),
                    h("Calmer Code Inbox"),
                    h("App Shows Bank Requests"),
                    h("Android Message Helper"),
                    h("Delivery Texts Sorted"),
                    h("OTP And Spam Review"),
                    h("Trial Renewal Info"),
                    h("Inbox Review Helper"),
                ],
                COMMON_DESCRIPTIONS,
            ),
        ],
        "scam_text_problem_scale": [
            rsa(
                "scam_text_control",
                [
                    h("Scam Text Messages", "query_echo"),
                    h("Phishing SMS Review"),
                    h("SMS Warning App"),
                    h("App Flags Prize Links"),
                    h("Bank Details Request"),
                    h("Smishing Text Helper"),
                    h("Before Sharing Details"),
                    h("Android Text Warnings"),
                    h("Prize Message Review"),
                    h("OTP Links In View"),
                    h("Review Aid Terms"),
                ],
                COMMON_DESCRIPTIONS,
            ),
            rsa(
                "scam_text_challenger",
                [
                    h("Text Scams In Inbox", "query_echo"),
                    h("Phishing SMS Helper"),
                    h("SMS Fraud Review"),
                    h("Scam Text App Review"),
                    h("App Shows Link Clues"),
                    h("Prize SMS Bank Details"),
                    h("Short Link Highlighted"),
                    h("Check Details First"),
                    h("Android SMS Alerts"),
                    h("Install Page Ready"),
                    h("Prize Text Review"),
                ],
                COMMON_DESCRIPTIONS,
            ),
        ],
        "otp_utility_risk_scale": [
            rsa(
                "otp_utility_control",
                [
                    h("OTP App For SMS Codes", "query_echo"),
                    h("OTP SMS Review"),
                    h("SMS App Code Review"),
                    h("App Shows Code Context"),
                    h("Bank Login Code Finder"),
                    h("Delivery OTP Check"),
                    h("Account Change Warning"),
                    h("Find Recent Codes"),
                    h("Service Alerts Nearby"),
                    h("Yearly Price Shown"),
                    h("Default OTP Inbox"),
                ],
                COMMON_DESCRIPTIONS,
            ),
            rsa(
                "otp_utility_challenger",
                [
                    h("OTP Fraud Review", "query_echo"),
                    h("Delivery OTP Scam Aid"),
                    h("OTP Warning App"),
                    h("App Flags Code Pressure"),
                    h("Bank OTP In View"),
                    h("Account Access Context"),
                    h("Compares Caller Claim"),
                    h("Recent Code Finder"),
                    h("Delivery Code Inbox"),
                    h("Code Help Listing"),
                    h("Code Review Terms"),
                ],
                COMMON_DESCRIPTIONS,
            ),
        ],
        "sms_organizer_control": [
            rsa(
                "sms_organizer_control",
                [
                    h("SMS Organizer", "query_echo"),
                    h("Default SMS App Inbox"),
                    h("Daily Text Sorting"),
                    h("App Organizes Codes"),
                    h("Bank Codes In View"),
                    h("Service Updates Grouped"),
                    h("Codes In One View"),
                    h("Cleaner Daily Inbox"),
                    h("Review Links Too"),
                    h("Subscription Price Clear"),
                    h("Setup Page Visible"),
                ],
                COMMON_DESCRIPTIONS,
            ),
            rsa(
                "sms_organizer_challenger",
                [
                    h("SMS Organiser App", "query_echo"),
                    h("Default SMS App For Codes"),
                    h("App Shows Login Codes"),
                    h("Daily Alerts Grouped"),
                    h("OTP Messages Together"),
                    h("Suspicious Links Marked"),
                    h("Daily Texts In View"),
                    h("Login SMS Faster"),
                    h("Calmer SMS Inbox"),
                    h("Price Details Visible"),
                    h("Play Page Visible"),
                ],
                COMMON_DESCRIPTIONS,
            ),
        ],
        "sms_classifier_brand_exact": [
            rsa(
                "brand_control",
                [
                    h("SMS Classifier App", "query_echo"),
                    h("Android SMS App"),
                    h("App Shows OTP Codes"),
                    h("Review Links In SMS"),
                    h("Bank Alerts Organized"),
                    h("Open Google Play"),
                    h("14 Day Pro Trial"),
                    h("INR 199 Per Year"),
                    h("Service Texts Sorted"),
                    h("Default SMS Helper"),
                    h("Warnings For Review"),
                ],
                COMMON_DESCRIPTIONS,
            ),
            rsa(
                "brand_challenger",
                [
                    h("SMS Classifier", "query_echo"),
                    h("App Flags Odd Links"),
                    h("OTP Inbox Included"),
                    h("Android Text Helper"),
                    h("Bank Codes In View"),
                    h("Review Before Reply"),
                    h("Play Store Listing"),
                    h("Pro Trial Terms"),
                    h("Service Alerts Sorted"),
                    h("Default SMS App"),
                    h("Open App Listing"),
                ],
                COMMON_DESCRIPTIONS,
            ),
        ],
        "sms_permissions_trust_holdout": [
            rsa(
                "permissions_control",
                [
                    h("SMS Permissions Android", "query_echo"),
                    h("Default SMS Permissions"),
                    h("Android SMS App"),
                    h("App Shows Data Choices"),
                    h("Review Feature Controls"),
                    h("Trial Details Visible"),
                    h("Play Listing Terms"),
                    h("SMS App Privacy"),
                    h("Cloud Review Explained"),
                    h("Settings Before Pro"),
                    h("Permission Review"),
                ],
                COMMON_DESCRIPTIONS,
            ),
            rsa(
                "permissions_challenger",
                [
                    h("SMS App Data Privacy", "query_echo"),
                    h("Default SMS App"),
                    h("App Shows Permissions"),
                    h("Review Data Choices"),
                    h("Android Text Privacy"),
                    h("Pro Trial Terms Clear"),
                    h("Feature Controls Visible"),
                    h("Open Play Listing"),
                    h("Settings Review First"),
                    h("SMS Permission Check"),
                    h("Data Choices Visible"),
                ],
                COMMON_DESCRIPTIONS,
            ),
        ],
    }


def polish_search_ad_groups(ad_groups: list[dict]) -> None:
    descriptions = {
        ("sms_app_category_scale", "messages_app_control"): [
            "The app organizes login messages, service alerts, and review-needed texts in one inbox.",
            "The app highlights odd links while keeping renewal terms visible.",
            "The app shows bank-code context without a fraud-prevention promise.",
            "The app explains trial pricing before the annual renewal.",
        ],
        ("sms_app_category_scale", "messages_app_challenger"): [
            "The app organizes daily messages without forcing a crowded default view.",
            "The app highlights review cues for odd links and account-code texts.",
            "The app finds recent login messages while service alerts stay easier to scan.",
            "The app shows Pro trial terms before the yearly price starts.",
        ],
        ("spam_sms_problem_scale", "spam_sms_control"): [
            "The app flags spam-looking texts and adds context before you reply.",
            "The app shows why a message may need review without blocking claims.",
            "The app organizes OTPs and service alerts beside suspicious-looking texts.",
            "The app lists trial terms so the paid renewal is clear.",
        ],
        ("spam_sms_problem_scale", "spam_sms_challenger"): [
            "The app highlights odd reply requests and bank-detail language.",
            "The app shows review cues while daily codes remain accessible.",
            "The app organizes spam-looking messages separately from routine alerts.",
            "The app flags links for review without calling every text unsafe.",
        ],
        ("scam_text_problem_scale", "scam_text_control"): [
            "The app highlights prize-style messages that ask for bank details.",
            "The app shows link-review cues before you tap or reply.",
            "The app flags suspicious-looking requests without certifying every SMS.",
            "The app keeps trial and renewal terms clear beside review features.",
        ],
        ("scam_text_problem_scale", "scam_text_challenger"): [
            "The app shows why a link or details request may need review.",
            "The app highlights phishing-style SMS with bounded review wording.",
            "The app organizes suspicious-looking texts near OTP and service messages.",
            "The app explains Pro review features before the yearly renewal.",
        ],
        ("otp_utility_risk_scale", "otp_utility_control"): [
            "The app shows code context before a bank OTP is shared under pressure.",
            "The app finds recent login messages while keeping account-change cues visible.",
            "The app organizes bank codes beside service alerts for quicker review.",
            "The app lists trial terms and yearly price before renewal.",
        ],
        ("otp_utility_risk_scale", "otp_utility_challenger"): [
            "The app highlights caller-code mismatch moments for review.",
            "The app shows why a requested code needs review before you reply.",
            "The app flags unusual requests while routine alerts stay visible.",
            "The app organizes recent OTPs so review happens before replies.",
        ],
        ("sms_organizer_control", "sms_organizer_control"): [
            "The app organizes OTPs and service messages for calmer daily scanning.",
            "The app shows bank-code cards while keeping suspicious links nearby.",
            "The app finds login messages without promising perfect sorting.",
            "The app explains trial and yearly renewal terms clearly.",
        ],
        ("sms_organizer_control", "sms_organizer_challenger"): [
            "The app highlights bank-code messages and separates routine alerts.",
            "The app organizes service texts while keeping review cues visible.",
            "The app shows recent OTP context before you copy or reply.",
            "The app flags suspicious-looking links as review aids only.",
        ],
        ("sms_classifier_brand_exact", "brand_control"): [
            "The app organizes OTP, link, and alert review moments after install.",
            "The app shows trial pricing and renewal details from the store page.",
            "The app flags suspicious-looking texts as bounded review cues.",
            "The app highlights settings and permission cues for cautious users.",
        ],
        ("sms_classifier_brand_exact", "brand_challenger"): [
            "The SMS Classifier app highlights OTP and suspicious-link review moments.",
            "The app organizes bank-code messages and service alerts in one inbox.",
            "The app shows trial details before the INR 199 yearly renewal.",
            "The app shows review labels with bounded safety wording.",
        ],
        ("sms_permissions_trust_holdout", "permissions_control"): [
            "The app shows permission context, Pro terms, and feature controls before setup.",
            "The app highlights review features with clear cloud-review context.",
            "The app shows data-choice cues from the settings and Play listing.",
            "The app highlights privacy questions before enabling Pro review features.",
        ],
        ("sms_permissions_trust_holdout", "permissions_challenger"): [
            "The app shows SMS permission choices and feature settings in plain language.",
            "The app shows cloud review context with bounded privacy wording.",
            "The app shows trial and renewal terms before Pro starts.",
            "The app highlights Play listing details for cautious users.",
        ],
    }
    headline_replacements = {
        ("sms_app_category_scale", "messages_app_control", "Scam Link Warnings"): "Suspicious Link Cues",
        ("sms_app_category_scale", "messages_app_challenger", "App Shows Odd Links"): "Highlights Odd Links",
        ("spam_sms_problem_scale", "spam_sms_challenger", "App Shows Bank Requests"): "Highlights Bank Requests",
        ("scam_text_problem_scale", "scam_text_control", "SMS Warning App"): "Suspicious SMS Review",
        ("scam_text_problem_scale", "scam_text_challenger", "SMS Warning App"): "Scam Text App Review",
        ("scam_text_problem_scale", "scam_text_challenger", "App Shows Link Clues"): "Shows Link Clues",
        ("otp_utility_risk_scale", "otp_utility_control", "App Shows Code Context"): "Shows Code Context",
        ("otp_utility_risk_scale", "otp_utility_challenger", "OTP Fraud Review"): "OTP Fraud Context",
        ("otp_utility_risk_scale", "otp_utility_challenger", "Delivery OTP Scam Aid"): "Delivery OTP Context",
        ("sms_organizer_control", "sms_organizer_challenger", "App Shows Login Codes"): "Shows Login Codes",
        ("sms_classifier_brand_exact", "brand_control", "App Shows OTP Codes"): "Shows OTP Codes",
        ("sms_classifier_brand_exact", "brand_challenger", "App Flags Odd Links"): "Highlights Odd Links",
        ("sms_permissions_trust_holdout", "permissions_control", "App Shows Data Choices"): "Shows Data Choices",
        ("sms_permissions_trust_holdout", "permissions_challenger", "App Shows Permissions"): "Shows Permissions",
    }
    headline_overrides = {
        ("sms_classifier_brand_exact", "brand_control"): [
            h("SMS Classifier App", "query_echo"),
            h("Official App Listing"),
            h("Shows OTP Context"),
            h("Flags Brand SMS"),
            h("Bank Code Review"),
            h("Play Store Page"),
            h("14 Day Pro Trial"),
            h("INR 199 Yearly"),
            h("Service Alert Inbox"),
            h("Brand Listing"),
            h("Review Labels Explained"),
        ],
        ("sms_classifier_brand_exact", "brand_challenger"): [
            h("SMS Classifier", "query_echo"),
            h("Review OTP Texts"),
            h("Highlights Link Reasons"),
            h("Messages Organized"),
            h("Bank SMS Context"),
            h("Pro Terms Visible"),
            h("Play Store Page"),
            h("Service SMS Inbox"),
            h("Suspicious Text Review"),
            h("Default Inbox Helper"),
            h("Trial Then Yearly"),
        ],
        ("sms_permissions_trust_holdout", "permissions_control"): [
            h("SMS Permissions Android", "query_echo"),
            h("Default SMS Permissions"),
            h("Shows Data Choices"),
            h("Permission Review"),
            h("Cloud Review Explained"),
            h("Trial Details Visible"),
            h("Feature Controls Visible"),
            h("Play Listing Terms"),
            h("SMS Privacy Info"),
            h("Pro Settings Context"),
            h("Data Choices Visible"),
        ],
        ("sms_permissions_trust_holdout", "permissions_challenger"): [
            h("SMS App Data Privacy", "query_echo"),
            h("Default SMS Permissions"),
            h("Shows Permissions"),
            h("Review Data Choices"),
            h("Android Text Privacy"),
            h("Pro Trial Terms"),
            h("Feature Controls Visible"),
            h("Cloud Review Context"),
            h("Play Listing Details"),
            h("Settings Review"),
            h("Permission Checklist"),
        ],
    }
    category_overrides = {
        "scam_text_problem_scale": ["scam text app", "phishing SMS", "suspicious SMS", "SMS review app"],
        "sms_classifier_brand_exact": ["SMS Classifier", "SMS Classifier app", "official app listing", "brand listing"],
        "sms_permissions_trust_holdout": ["SMS privacy", "SMS permissions", "SMS app", "default SMS app"],
    }
    for group in ad_groups:
        gid = group["id"]
        if gid in category_overrides:
            group["category_terms"] = category_overrides[gid]
        for item in group.get("rsas", []):
            rid = item["id"]
            if (gid, rid) in headline_overrides:
                item["headlines"] = headline_overrides[(gid, rid)]
            else:
                for headline in item.get("headlines", []):
                    key = (gid, rid, headline.get("text") if isinstance(headline, dict) else headline)
                    if key in headline_replacements:
                        headline["text"] = headline_replacements[key]
            if (gid, rid) in descriptions:
                item["descriptions"] = descriptions[(gid, rid)]
        if gid in {"sms_classifier_brand_exact", "sms_permissions_trust_holdout"}:
            group["rsas"] = group.get("rsas", [])[:1]


def patch_search_pack() -> None:
    clusters = search_groups()
    rsas_by_group = search_rsas()
    ad_groups = []
    for group in clusters:
        merged = dict(group)
        merged["rsas"] = rsas_by_group[group["id"]]
        ad_groups.append(merged)
    polish_search_ad_groups(ad_groups)

    dump_yaml(
        "keyword_clusters.yaml",
        {
            "market": "India",
            "language": "English",
            "brand_name": "SMS Classifier",
            "recommended_launch_match": "Exact and phrase for the five volume groups first; defensive brand/trust holdouts stay exact/low-budget.",
            "volume_refresh": {
                "source": "keyword_planner_api_live_2026-06-27",
                "launch_volume_groups_monthly_searches": sum(
                    item["estimated_monthly_searches"] for item in clusters if isinstance(item["priority"], int)
                ),
                "defensive_groups": ["sms_classifier_brand_exact", "sms_permissions_trust_holdout"],
            },
            "clusters": clusters,
            "negative_keywords_initial": shared_negatives(),
        },
    )
    dump_yaml(
        "google_search_copy.yaml",
        {
            "metadata": {
                "product": "SMS Classifier",
                "campaign_type": "Google Search RSA",
                "status": "v2_quality_fixed_high_volume_candidate",
                "dynamic_copy_plan": "Static RSAs first; DKI only after search terms and negatives are reviewed.",
                "ai_max_guardrail": "Review generated variants against claim boundaries and monetization terms.",
            },
            "brand_name": "SMS Classifier",
            "require_brand_ad_group": True,
            "require_trust_ad_group": True,
            "ad_groups": ad_groups,
        },
    )
    dump_yaml(
        "search_intent_map.yaml",
        {
            "intents": [
                {
                    "ad_group_id": item["id"],
                    "persona_id": item["persona_id"],
                    "search_moment": item["search_moment"],
                    "primary_query": item["primary_query"],
                    "desired_outcome": item["primary_promise"],
                    "claim_boundary": item["claim_boundary"],
                    "estimated_monthly_searches": item["estimated_monthly_searches"],
                    "priority": item["priority"],
                }
                for item in clusters
            ]
        },
    )


def make_contact_sheet() -> None:
    paths = sorted((RUN / "assets").glob("IMG_*.png"))
    if not paths:
        return
    cols = 3
    thumb = 300
    pad = 20
    label_h = 54
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (thumb + pad) + pad, rows * (thumb + label_h + pad) + pad), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb, thumb), Image.LANCZOS)
        x = pad + (idx % cols) * (thumb + pad)
        y = pad + (idx // cols) * (thumb + label_h + pad)
        bg = Image.new("RGB", (thumb, thumb), "#F5F5F5")
        bg.paste(image, ((thumb - image.width) // 2, (thumb - image.height) // 2))
        sheet.paste(bg, (x, y))
        draw.text((x, y + thumb + 8), path.name[:42], fill=(0, 0, 0), font=font(14))
    sheet.save(RUN / "evals/codex_review/v2_static_contact_sheet.jpg", quality=92)


def write_fix_log() -> None:
    (RUN / "EVAL_FIX_LOG.md").write_text(
        """# Eval Fix Log

Applied after the first deterministic preflight caught copy/Search failures.

- Changed the prize hook from app-first wording to a pain-first bank-details hook.
- Changed the OTP organizer hook so the product action uses evaluator-recognized agency and carries the less-stress stake.
- Strengthened the OTP organizer emotional payoff with a bank-login OTP stake.
- Changed the final video caption from advice-only to product-aided outcome.
- Rebuilt Search around five volume clusters plus exact defensive brand/trust holdouts.
- Rewrote RSA descriptions so sampled combinations retain product agency without unsafe absolute claims.
- Rerendered all static assets after headline changes.
""",
        encoding="utf-8",
    )


def main() -> int:
    patch_core_copy()
    patch_static_assets()
    patch_search_pack()
    make_contact_sheet()
    write_fix_log()
    print("applied_quality_fixes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
