from __future__ import annotations

import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont


CENTRAL = Path(r"D:\Projects\ad creatives")
TARGET = Path(r"D:\Projects\SMS datasets and project\android_sms_classifier")
ADS_ROOT = TARGET.parent / "ads"
OLD_RUN = ADS_ROOT / "2026-06-27-google-ads-live-launch-v1"
RUN = ADS_ROOT / "2026-06-27-google-ads-creative-quality-refresh-v2"

sys.path.insert(0, str(CENTRAL))
from adengine.brandkit import load_brand_kit  # noqa: E402
from adengine.compositor import render  # noqa: E402
from adengine.io import file_sha256  # noqa: E402


def write_text(rel: str, text: str) -> None:
    (RUN / rel).parent.mkdir(parents=True, exist_ok=True)
    (RUN / rel).write_text(text.strip() + "\n", encoding="utf-8")


def dump_yaml(rel: str, data) -> None:
    (RUN / rel).parent.mkdir(parents=True, exist_ok=True)
    (RUN / rel).write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=False, width=110),
        encoding="utf-8",
    )


def dump_json(rel: str, data) -> None:
    (RUN / rel).parent.mkdir(parents=True, exist_ok=True)
    (RUN / rel).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def font(size: int, bold: bool = False):
    paths = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, box, radius: int, fill: str, outline: str | None = None, width: int = 2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def make_dirs() -> None:
    for sub in [
        "inputs",
        "screenshots",
        "assets",
        "assets/video",
        "assets/audio",
        "assets/video_props",
        "exports",
        "exports/launch_ready",
        "references",
        "evals",
        "evals/codex_review",
        "tools",
    ]:
        (RUN / sub).mkdir(parents=True, exist_ok=True)


def seed_logo() -> Path:
    source_icon = TARGET / "store_assets" / "app-icon.png"
    if not source_icon.exists():
        source_icon = TARGET / "store_assets" / "SMS Classifier Store APP ICON.png"
    dest = RUN / "inputs" / "logo-primary.png"
    shutil.copy2(source_icon, dest)
    return dest


def copy_keyword_sources() -> None:
    for name in ("keyword_research.csv", "keyword_research_volume_expansion.csv"):
        src = OLD_RUN / name
        if src.exists():
            shutil.copy2(src, RUN / name)


def write_core_docs(now: str) -> None:
    write_text(
        "product_context.md",
        """
---
product_type: mobile_app
product_name: SMS Classifier
market: India
language: English
primary_goal: app_install
brand_kit_status: ready
---

# Product Context - SMS Classifier Creative Quality Refresh V2

SMS Classifier is an Android default-SMS helper that organizes OTP, service, and review-needed messages so people can find codes and review suspicious-looking texts faster.

Primary audience: Android users in India who receive OTPs, delivery messages, bank/service alerts, spam texts, and suspicious links. Secondary audience: family helpers who want parents or relatives to notice risky-looking SMS moments before sharing codes or tapping links.

Offer: 14-day Pro trial. Pro annual subscription is INR 199/year in India. Do not position the app as permanently free in ad copy.

Claim boundaries: use helps, highlights, shows, warns, flags, makes easier to review, and keeps messages organized. Avoid guarantees, blocks all scams, prevents every fraud, reads every intent perfectly, messages never leave the device, and 100% safe language.

This refresh specifically fixes the prior set's critique: no blank logo placeholder, more diverse visual systems, larger in-phone proof text, one-hook video with distinct proof beats, and Search copy aligned to the higher-volume Keyword Planner source.
""",
    )
    dump_yaml(
        "monetization.yaml",
        {
            "monetization": {
                "pricing_model": "free_trial",
                "has_free_tier": True,
                "trial_days": 14,
                "price": 199,
                "currency": "INR",
                "billing_period": "year",
                "notes": "Local OTP detection/basic use is available; Pro trial/subscription enables cloud classification, code-purpose explanations, scam warnings, and do-not-share alerts. Annual Google Play subscription is INR 199/year in India.",
            }
        },
    )
    dump_yaml(
        "run_manifest.yaml",
        {
            "target_project": str(TARGET),
            "campaign_slug": "google-ads-creative-quality-refresh-v2",
            "created_at": now,
            "central_engine_path": str(CENTRAL),
            "central_engine_commit": "4052b4b",
            "product_type": "mobile_app",
            "requested_outputs": [
                "google_app_static_images",
                "youtube_shorts_video",
                "google_search_copy",
                "evals",
                "client_summary",
            ],
            "product_context_status": "created_from_prior_confirmed_context",
            "user_approval_status": "not_approved_for_spend",
            "stakes_map_status": "created",
            "hook_gate_status": "created",
            "message_map_status": "created",
            "copy_preflight_status": "pending",
            "proof_authoring_status": "created",
            "creative_quality_eval_status": "pending",
            "checker_model_review_status": "pending",
            "learning_capture_status": "pending",
            "artifact_index": {
                "old_run_superseded": str(OLD_RUN),
                "new_run": str(RUN),
                "launch_ready_dir": "exports/launch_ready",
            },
            "notes": [
                "All assets must keep parent campaigns paused until explicit approval to serve.",
                "Old v1 launch folder is superseded and should not be enabled as-is.",
                "Search uses high-volume Keyword Planner source from the same day prior run, not the stale low-volume 5-group publish.",
            ],
        },
    )


def write_brand_kit() -> None:
    dump_yaml(
        "brand_kit.yaml",
        {
            "brand_name": "SMS Classifier",
            "logo_files": [
                {"path": "inputs/logo-primary.png", "variant": "primary", "min_clearspace_pct": 0.25},
                {"path": "inputs/logo-primary.png", "variant": "icon", "min_clearspace_pct": 0.25},
                {"path": "inputs/logo-primary.png", "variant": "mono_dark", "min_clearspace_pct": 0.25},
                {"path": "inputs/logo-primary.png", "variant": "mono_light", "min_clearspace_pct": 0.25},
            ],
            "palette": {
                "primary": "#1D9BF0",
                "secondary": ["#F59E0B", "#10B981", "#7C3AED", "#BBD7F2"],
                "background_light": "#F7FBFF",
                "background_dark": "#08111F",
                "text_on_light": "#102033",
                "text_on_dark": "#F8FAFC",
                "accent_warning": "#C2410C",
                "accent_ok": "#15803D",
            },
            "fonts": {"heading": "Inter", "body": "Inter", "fallback": "Segoe UI, Arial, sans-serif"},
            "tone": ["clear", "practical", "privacy-aware", "calm"],
            "voice_dos": [
                "Use decision-aid language: helps, highlights, shows, warns, flags, easier to find.",
                "Keep fraud and OTP claims bounded.",
                "Use natural Indian English for consumer acquisition.",
            ],
            "voice_donts": [
                "Do not claim the app stops every scam.",
                "Do not use bare free CTAs for trial-then-paid surfaces.",
                "Do not use fake OS warnings or real OTPs.",
            ],
            "logo_rules": {
                "clearspace": "Keep at least 25% icon-width clearspace.",
                "backgrounds": "Use high contrast.",
            },
            "forbidden": ["100% safe", "safe and secure", "never miss", "blocks all scams", "install free", "download free"],
        },
    )


def write_strategy_files() -> list[dict[str, str]]:
    stakes = {
        "product_name": "SMS Classifier",
        "product_category": "Android SMS warning and organizer app",
        "market": "India",
        "language": "English",
        "target_user_profile": {
            "language_register": "consumer",
            "natural_terms": [
                "SMS",
                "SMS app",
                "OTP",
                "bank OTP",
                "spam texts",
                "scam SMS",
                "suspicious link",
                "messages app",
                "bank details",
                "SMS Classifier",
                "classifier",
            ],
            "domain_terms": ["classification", "intent", "risk signal", "cloud checks", "model"],
            "proof_terms": ["Review tab", "OTP inbox", "flagged message"],
            "avoid_terms": ["100% safe", "scam proof", "blocks all scams", "safe and secure"],
            "required_language_variants": [],
        },
        "personas": [
            {
                "id": "otp_fraud_worrier",
                "name": "Android user under OTP pressure",
                "description": "Receives OTPs and bank/service alerts and wants context before sharing or tapping.",
            },
            {
                "id": "busy_otp_user",
                "name": "Busy OTP finder",
                "description": "Needs login or delivery codes quickly in a crowded SMS inbox.",
            },
            {
                "id": "family_helper",
                "name": "Family helper",
                "description": "Helps relatives notice suspicious SMS moments without fear-based wording.",
            },
        ],
        "moments": [
            {
                "id": "scam_prize_details",
                "trigger": "A prize-style SMS asks for bank details",
                "stakes": "Tapping or sharing details can expose money or credentials.",
            },
            {
                "id": "delivery_otp_pressure",
                "trigger": "A caller says the OTP is for delivery",
                "stakes": "The SMS context suggests account access or account change instead.",
            },
            {
                "id": "login_code_hurry",
                "trigger": "A bank login code is buried in service messages",
                "stakes": "The user wastes time and may copy the wrong code under pressure.",
            },
        ],
        "features": [
            {
                "id": "suspicious_link_warning",
                "mechanism": "The app marks suspicious-looking links or details requests for review.",
                "bad_outcome_defeated": "Tapping a suspicious link or sharing bank details too quickly.",
                "outcome_type": "fraud_avoidance",
                "so_what_ladder": [
                    "The SMS asks for bank details.",
                    "The app keeps the warning visible before tapping.",
                    "The user can avoid sharing details with a scam text.",
                ],
            },
            {
                "id": "otp_context_warning",
                "mechanism": "The app surfaces context around OTP messages that need review.",
                "bad_outcome_defeated": "Sharing an account-change code under a false delivery pretext.",
                "outcome_type": "fraud_avoidance",
                "so_what_ladder": [
                    "Someone says the code is for delivery.",
                    "The app shows account-change context.",
                    "The user can avoid sharing an account access OTP.",
                ],
            },
            {
                "id": "otp_inbox_sorting",
                "mechanism": "The app groups recent OTP and service messages for quicker review.",
                "bad_outcome_defeated": "Losing the right login code inside a crowded inbox.",
                "outcome_type": "risk_reduction",
                "so_what_ladder": [
                    "A login code is hard to find.",
                    "The app brings OTPs into a clearer inbox.",
                    "The user can avoid delay or copying the wrong SMS.",
                ],
            },
        ],
        "scenarios": [
            {
                "id": "scenario_prize_bank_details",
                "persona_id": "otp_fraud_worrier",
                "moment_id": "scam_prize_details",
                "feature_id": "suspicious_link_warning",
                "bad_outcome": "A scam text collects bank details through a suspicious link.",
                "user_decision_enabled": "Review before tapping or sharing details.",
                "claim_boundary": "Helps flag suspicious-looking SMS; does not certify every text as safe or unsafe.",
                "outcome_type": "fraud_avoidance",
                "so_what_ladder": [
                    "The text says the user won a prize.",
                    "The app shows the bank-details warning.",
                    "The user can avoid sharing details with a scam SMS.",
                ],
            },
            {
                "id": "scenario_delivery_account_otp",
                "persona_id": "family_helper",
                "moment_id": "delivery_otp_pressure",
                "feature_id": "otp_context_warning",
                "bad_outcome": "A caller uses delivery pressure to get an account-change OTP.",
                "user_decision_enabled": "Do not share until the OTP context matches the claim.",
                "claim_boundary": "Shows context and review labels; does not guarantee fraud prevention.",
                "outcome_type": "fraud_avoidance",
                "so_what_ladder": [
                    "The caller says delivery.",
                    "The app shows account-change context.",
                    "The user can avoid sharing an account access OTP.",
                ],
            },
            {
                "id": "scenario_bank_otp_buried",
                "persona_id": "busy_otp_user",
                "moment_id": "login_code_hurry",
                "feature_id": "otp_inbox_sorting",
                "bad_outcome": "A bank login code is missed or confused with another SMS.",
                "user_decision_enabled": "Find and copy the right OTP faster.",
                "claim_boundary": "Organizes and surfaces codes; does not guarantee perfect sorting.",
                "outcome_type": "risk_reduction",
                "so_what_ladder": [
                    "The bank login SMS is buried.",
                    "The app groups OTPs and service codes.",
                    "The user can avoid delay or copying the wrong SMS.",
                ],
            },
        ],
    }
    dump_yaml("stakes_map.yaml", stakes)

    approved_hooks = [
        {
            "id": "H_SCAM_PRIZE",
            "status": "primary",
            "rank": 1,
            "hook": "Prize SMS says you won. App shows bank risk.",
            "hook_type": "pain_led",
            "persona_id": "otp_fraud_worrier",
            "moment_id": "scam_prize_details",
            "scenario_id": "scenario_prize_bank_details",
            "feature_id": "suspicious_link_warning",
            "proof_id": "proof_scam_prize_warning",
            "claim_boundary": "Helps flag suspicious-looking SMS; does not certify every text as safe or unsafe.",
            "proof_feasibility": "high",
            "evidence_status": "source_confirmed",
            "confidence": "source_confirmed",
            "outcome_type": "fraud_avoidance",
            "so_what_ladder": [
                "The text says the user won a prize.",
                "The app shows the bank-details warning.",
                "The user can avoid sharing details with a scam SMS.",
            ],
            "scores": {
                "pain_magnitude": 5,
                "frequency": 4,
                "breadth_of_audience": 4,
                "proofability": 5,
                "differentiation": 4,
                "one_second_clarity": 5,
                "claim_safety": 5,
            },
        },
        {
            "id": "H_OTP_ACCOUNT",
            "status": "approved",
            "rank": 2,
            "hook": "Caller says delivery OTP. SMS app shows account change.",
            "hook_type": "pain_led",
            "persona_id": "family_helper",
            "moment_id": "delivery_otp_pressure",
            "scenario_id": "scenario_delivery_account_otp",
            "feature_id": "otp_context_warning",
            "proof_id": "proof_otp_account_warning",
            "claim_boundary": "Shows OTP context and review labels; does not guarantee fraud prevention.",
            "proof_feasibility": "high",
            "evidence_status": "source_confirmed",
            "confidence": "source_confirmed",
            "outcome_type": "fraud_avoidance",
            "so_what_ladder": [
                "The caller says delivery.",
                "The app shows account-change context.",
                "The user can avoid sharing an account access OTP.",
            ],
            "scores": {
                "pain_magnitude": 5,
                "frequency": 3,
                "breadth_of_audience": 4,
                "proofability": 5,
                "differentiation": 5,
                "one_second_clarity": 5,
                "claim_safety": 5,
            },
        },
        {
            "id": "H_OTP_INBOX",
            "status": "approved",
            "rank": 3,
            "hook": "Bank login SMS is buried. App finds the OTP.",
            "hook_type": "benefit_led",
            "persona_id": "busy_otp_user",
            "moment_id": "login_code_hurry",
            "scenario_id": "scenario_bank_otp_buried",
            "feature_id": "otp_inbox_sorting",
            "proof_id": "proof_otp_inbox_focus",
            "claim_boundary": "Organizes and surfaces codes; does not guarantee perfect sorting.",
            "proof_feasibility": "high",
            "evidence_status": "source_confirmed",
            "confidence": "source_confirmed",
            "outcome_type": "risk_reduction",
            "so_what_ladder": [
                "The bank login SMS is buried.",
                "The app groups OTPs and service codes.",
                "The user can avoid delay or copying the wrong SMS.",
            ],
            "scores": {
                "pain_magnitude": 4,
                "frequency": 5,
                "breadth_of_audience": 5,
                "proofability": 5,
                "differentiation": 4,
                "one_second_clarity": 5,
                "claim_safety": 5,
            },
        },
    ]
    dump_yaml(
        "hooks.yaml",
        {
            "approved_hooks": approved_hooks,
            "discarded_hooks": [
                {"hook": "Pause before tapping", "reason": "Advice-only and product agency too weak."},
                {"hook": "App flags KYC risk", "reason": "Compressed jargon for broad acquisition."},
            ],
        },
    )
    dump_yaml(
        "message_map.yaml",
        {
            "messages": [
                {
                    "hook_id": "H_SCAM_PRIZE",
                    "proof_id": "proof_scam_prize_warning",
                    "on_image_headline": "Prize SMS says you won. App shows bank risk.",
                    "headline_tests": [
                        {"id": "short_prize", "on_image_headline": "Prize SMS asks for bank details."}
                    ],
                    "platform_headlines": ["Scam SMS Warning App", "Review Suspicious SMS", "SMS Classifier"],
                    "long_headlines": [
                        "SMS Classifier helps flag suspicious prize-style texts before bank details are shared."
                    ],
                    "platform_descriptions": [
                        "Review suspicious-looking SMS links and details requests in a clearer default SMS inbox."
                    ],
                    "cta_variants": ["Start 14-day trial", "Open on Google Play"],
                    "category_context": "SMS warning app",
                    "plain_language_pain": "A scam SMS can ask for bank details through a prize link.",
                    "story_framework": "demo_proof",
                    "emotional_payoff": "More confidence before sharing bank details or tapping a suspicious SMS.",
                },
                {
                    "hook_id": "H_OTP_ACCOUNT",
                    "proof_id": "proof_otp_account_warning",
                    "on_image_headline": "Caller says delivery OTP. SMS app shows account change.",
                    "headline_tests": [
                        {"id": "short_delivery", "on_image_headline": "Delivery OTP? SMS app shows context."}
                    ],
                    "platform_headlines": ["OTP Warning App", "Review Delivery OTPs", "SMS Classifier"],
                    "long_headlines": [
                        "SMS Classifier helps show OTP context before a code is shared under pressure."
                    ],
                    "platform_descriptions": [
                        "See review-needed OTP context in your SMS inbox before replying or sharing a code."
                    ],
                    "cta_variants": ["Start 14-day trial", "Open on Google Play"],
                    "category_context": "SMS warning app",
                    "plain_language_pain": "A caller may pressure someone to share an OTP for the wrong account action.",
                    "story_framework": "demo_proof",
                    "emotional_payoff": "A calmer moment before sharing an OTP tied to account access.",
                },
                {
                    "hook_id": "H_OTP_INBOX",
                    "proof_id": "proof_otp_inbox_focus",
                    "on_image_headline": "Bank login SMS is buried. App finds the OTP.",
                    "headline_tests": [
                        {"id": "short_otp", "on_image_headline": "Bank OTPs are easier to find."}
                    ],
                    "platform_headlines": ["OTP Inbox Organizer", "Find Bank OTPs Fast", "SMS Classifier"],
                    "long_headlines": [
                        "SMS Classifier organizes OTP and service texts so login codes are easier to find."
                    ],
                    "platform_descriptions": [
                        "Find recent codes and review service SMS in a calmer default SMS inbox."
                    ],
                    "cta_variants": ["Start 14-day trial", "Open on Google Play"],
                    "category_context": "SMS organizer app",
                    "plain_language_pain": "A bank login SMS can disappear inside daily service messages.",
                    "story_framework": "demo_proof",
                    "emotional_payoff": "Less stress when a login code is needed quickly.",
                },
            ]
        },
    )
    write_text(
        "creative_strategy.md",
        """
# Creative Strategy

Product type: mobile app. Matched signals: Android package, Google Play app-install goal, mobile screenshots, SMS default-app UX.

Primary launch hypothesis: high-stakes SMS moments with visible product agency will outperform generic SMS organizer copy because the viewer sees what the app changes before tapping or sharing.

Approved concept families:

1. Prize SMS says you won. App shows bank risk.
2. Caller says delivery OTP. SMS app shows account change.
3. Bank login SMS is buried. App finds the OTP.

Measurement hypothesis: use the scam-link video and the three static families as separate App campaign asset signals. Keep Search separate and launch only the high-volume plan after plan/eval parity is verified.
""",
    )
    dump_yaml(
        "copy_candidates.yaml",
        {
            "selected": [item["hook"] for item in approved_hooks],
            "rejected": [
                {"hook": "Pause before tapping", "reason": "Advice-only and product agency too weak."},
                {"hook": "App flags KYC risk", "reason": "Compressed jargon for broad acquisition."},
            ],
        },
    )
    return approved_hooks


def make_phone_screen(path: Path, theme: dict[str, str], subtitle: str, cards: list[dict], active: str, logo_path: Path) -> None:
    icon = Image.open(logo_path).convert("RGBA")
    img = Image.new("RGB", (1080, 1920), theme["bg"])
    draw = ImageDraw.Draw(img)
    draw.text((64, 64), "9:41", fill=theme["text"], font=font(54, True))
    icon.thumbnail((86, 86), Image.LANCZOS)
    img.paste(icon, (64, 164), icon)
    draw.text((170, 170), "SMS Classifier", fill=theme["text"], font=font(60, True))
    draw.text((170, 238), subtitle, fill=theme["muted"], font=font(34))
    x = 64
    for tab in ["OTP", "Review", "Inbox"]:
        width = 190 if tab != "Review" else 230
        fill = theme["primary"] if tab == active else theme["chip"]
        text_color = "white" if tab == active else theme["text"]
        rounded(draw, (x, 340, x + width, 410), 35, fill)
        text_width = draw.textlength(tab, font=font(34, True))
        draw.text((x + (width - text_width) / 2, 356), tab, fill=text_color, font=font(34, True))
        x += width + 28
    y = 520
    for card in cards:
        height = card.get("h", 300)
        rounded(
            draw,
            (64, y, 1016, y + height),
            40,
            card.get("fill", "white"),
            outline=card.get("outline", "#D7E8F8"),
            width=3,
        )
        draw.text((104, y + 48), card["title"], fill=theme["text"], font=font(card.get("title_size", 52), True))
        if card.get("body"):
            draw.text((104, y + 120), card["body"], fill=theme["muted"], font=font(card.get("body_size", 36)))
        if card.get("badge"):
            bx, by = 104, y + height - 86
            bw = int(draw.textlength(card["badge"], font=font(31, True))) + 54
            rounded(draw, (bx, by, bx + bw, by + 58), 29, card.get("badge_fill", theme["primary"]))
            draw.text((bx + 27, by + 12), card["badge"], fill="white", font=font(31, True))
        y += height + 52
    nav_y = 1740
    for idx, label in enumerate(["Inbox", "Review", "OTP", "Settings"]):
        cx = 145 + idx * 265
        color = theme["primary"] if label == active else "#B9CDDD"
        draw.ellipse((cx - 18, nav_y, cx + 18, nav_y + 36), fill=color)
        text_width = draw.textlength(label, font=font(28))
        draw.text((cx - text_width / 2, nav_y + 60), label, fill=theme["muted"], font=font(28))
    img.save(path)


def write_screens_and_proofs(now: str, logo_path: Path) -> None:
    light = {"bg": "#F4FAFF", "text": "#102033", "muted": "#42566D", "primary": "#1D9BF0", "chip": "#E4F0FA"}
    warm = {"bg": "#FFF7ED", "text": "#102033", "muted": "#5B6470", "primary": "#D97706", "chip": "#FFEBCD"}
    mint = {"bg": "#F2FCF7", "text": "#102033", "muted": "#42566D", "primary": "#169B62", "chip": "#DDF7EA"}
    make_phone_screen(
        RUN / "screenshots/proof_scam_prize_warning.png",
        warm,
        "Messages that need review",
        [
            {
                "title": "Prize SMS says you won",
                "body": "Asks for bank details",
                "badge": "Suspicious link",
                "fill": "#FFF1DC",
                "outline": "#F3C27A",
                "badge_fill": "#C2410C",
                "h": 330,
            },
            {
                "title": "App warning stays visible",
                "body": "Review before tapping",
                "badge": "Open with caution",
                "fill": "#FFFFFF",
                "badge_fill": "#1D9BF0",
                "h": 300,
            },
        ],
        "Review",
        logo_path,
    )
    make_phone_screen(
        RUN / "screenshots/proof_scam_link_reason.png",
        warm,
        "Why this text is marked",
        [
            {
                "title": "Short link hidden",
                "body": "Bank details requested",
                "badge": "Check first",
                "fill": "#FFF1DC",
                "outline": "#F3C27A",
                "badge_fill": "#C2410C",
                "h": 330,
            },
            {
                "title": "Outside app request",
                "body": "Treat as suspicious",
                "badge": "Warning remains",
                "fill": "#FFFFFF",
                "badge_fill": "#1D9BF0",
                "h": 300,
            },
        ],
        "Review",
        logo_path,
    )
    make_phone_screen(
        RUN / "screenshots/proof_scam_review_done.png",
        warm,
        "Review-needed SMS",
        [
            {
                "title": "Suspicious text remains marked",
                "body": "Bank details request",
                "badge": "Review first",
                "fill": "#FFF1DC",
                "outline": "#F3C27A",
                "badge_fill": "#C2410C",
                "h": 330,
            },
            {
                "title": "No bank brand assumed",
                "body": "Generic demo text",
                "badge": "Claim bounded",
                "fill": "#FFFFFF",
                "badge_fill": "#169B62",
                "h": 300,
            },
        ],
        "Review",
        logo_path,
    )
    make_phone_screen(
        RUN / "screenshots/proof_otp_account_warning.png",
        light,
        "Messages that need review",
        [
            {
                "title": "Caller says delivery OTP",
                "body": "Code changes account",
                "badge": "Do not share yet",
                "fill": "#FFE6E4",
                "outline": "#F3A7A1",
                "badge_fill": "#B42318",
                "h": 330,
            },
            {
                "title": "App shows the mismatch",
                "body": "Review before sharing",
                "badge": "Account warning",
                "fill": "#FFFFFF",
                "badge_fill": "#1D9BF0",
                "h": 300,
            },
        ],
        "Review",
        logo_path,
    )
    make_phone_screen(
        RUN / "screenshots/proof_otp_inbox_focus.png",
        mint,
        "OTP and service codes",
        [
            {
                "title": "Bank login SMS found",
                "body": "Code ready when needed",
                "badge": "Copy code",
                "fill": "#EAFBF2",
                "outline": "#A7E7C1",
                "badge_fill": "#169B62",
                "h": 330,
            },
            {
                "title": "Delivery code separate",
                "body": "Already reviewed",
                "badge": "Less clutter",
                "fill": "#FFFFFF",
                "badge_fill": "#1D9BF0",
                "h": 300,
            },
        ],
        "OTP",
        logo_path,
    )
    screenshot_rows = [
        ("proof_scam_prize_warning", "Prize SMS bank-detail warning", "screenshots/proof_scam_prize_warning.png"),
        ("proof_scam_link_reason", "Suspicious link reason", "screenshots/proof_scam_link_reason.png"),
        ("proof_scam_review_done", "Warning stays visible", "screenshots/proof_scam_review_done.png"),
        ("proof_otp_account_warning", "Delivery OTP account-change warning", "screenshots/proof_otp_account_warning.png"),
        ("proof_otp_inbox_focus", "Bank OTP inbox focus", "screenshots/proof_otp_inbox_focus.png"),
    ]
    dump_yaml(
        "screenshots.yaml",
        {
            "source": "generated_ad_scale_demo_screens_with_real_icon",
            "created_at": now,
            "screenshots": [
                {
                    "id": sid,
                    "screen_name": name,
                    "key_state": name,
                    "suggested_use": ["strict_app_install", "ad_scale_product_proof"],
                    "crop_pct": {"top": 0, "right": 0, "bottom": 24, "left": 0},
                    "focus_pct": {"x": 50, "y": 40},
                    "path": path,
                }
                for sid, name, path in screenshot_rows
            ],
        },
    )
    proof_data = [
        (
            "proof_scam_prize_warning",
            "screenshots/proof_scam_prize_warning.png",
            "Suspicious link warning and bank details request",
            "The app warns before a prize SMS asks for bank details.",
            ["Prize SMS says you won", "Asks for bank details", "Suspicious link"],
            "sms_review_screen",
            "Shows the suspicious request and the product warning state, not just a headline.",
            "#FFF7ED",
            "#C2410C",
        ),
        (
            "proof_scam_link_reason",
            "screenshots/proof_scam_link_reason.png",
            "Short-link and bank-details reason",
            "The app gives a simple reason for the warning.",
            ["Short link hidden", "Bank details requested", "Check first"],
            "sms_review_screen",
            "Adds the reason behind the suspicious SMS warning.",
            "#FFF7ED",
            "#C2410C",
        ),
        (
            "proof_scam_review_done",
            "screenshots/proof_scam_review_done.png",
            "Warning remains visible after review",
            "The suspicious text remains marked for review.",
            ["Suspicious text remains marked", "Bank details request", "Review first"],
            "sms_review_screen",
            "Shows the payoff state that the warning stays visible.",
            "#FFF7ED",
            "#169B62",
        ),
        (
            "proof_otp_account_warning",
            "screenshots/proof_otp_account_warning.png",
            "Caller claim versus account-change warning",
            "The app shows account-change context before sharing a delivery OTP.",
            ["Caller says delivery OTP", "Code changes account", "Do not share yet"],
            "sms_review_screen",
            "Shows a contradiction between the caller claim and the code context.",
            "#F4FAFF",
            "#B42318",
        ),
        (
            "proof_otp_inbox_focus",
            "screenshots/proof_otp_inbox_focus.png",
            "Bank OTP separated in OTP inbox",
            "The app surfaces a bank login SMS so the code is easier to find.",
            ["Bank login SMS found", "Code ready when needed", "Copy code"],
            "sms_inbox",
            "Shows code organization and retrieval rather than only describing an organizer.",
            "#F2FCF7",
            "#169B62",
        ),
    ]
    dump_yaml(
        "proof_specs.yaml",
        {
            "proofs": [
                {
                    "id": pid,
                    "source": source,
                    "proof_type": "synthetic_ad_scale_product_ui",
                    "synthetic_data": True,
                    "max_visible_rows": 2,
                    "highlighted_state": highlighted,
                    "intended_proof_moment": moment,
                    "required_visible_text": required,
                    "forbidden_surfaces": [
                        "settings",
                        "debug",
                        "fake_os_alert",
                        "real_bank_brand",
                        "real_url",
                        "real_otp",
                    ],
                    "crop_pct": {"top": 0, "right": 0, "bottom": 24, "left": 0},
                    "focus_pct": {"x": 50, "y": 40},
                    "ad_scale_readability": "thumbnail_safe",
                    "proof_typography": {
                        "min_important_text_px": 52,
                        "max_visible_text_blocks": 3,
                        "max_words_per_block": 6,
                    },
                    "product_surface": surface,
                    "visual_adds": visual_adds,
                    "context_type": "realistic_sms_review_state",
                    "contrast_checks": [
                        {"fg": "#102033", "bg": bg, "min_ratio": 4.5},
                        {"fg": "#FFFFFF", "bg": badge, "min_ratio": 4.5},
                    ],
                }
                for pid, source, highlighted, moment, required, surface, visual_adds, bg, badge in proof_data
            ]
        },
    )


def write_creative_matrix_and_render() -> None:
    ratio_specs = {
        "SQUARE": ("google_app_square", "1:1", "1200x1200", 1200, 1200),
        "LANDSCAPE": ("google_app_landscape", "1.91:1", "1200x628", 1200, 628),
        "PORTRAIT": ("google_app_portrait", "4:5", "1200x1500", 1200, 1500),
    }
    concepts = [
        {
            "prefix": "IMG_SCAM_PRIZE",
            "hook_id": "H_SCAM_PRIZE",
            "proof_id": "proof_scam_prize_warning",
            "headline": "Prize SMS says you won. App shows bank risk.",
            "ad_group": "scam_sms_warning",
            "proof": "screenshots/proof_scam_prize_warning.png",
            "theme": "warm",
            "bg": "#FFF7ED",
            "mode": "light",
            "hook_type": "pain_led",
        },
        {
            "prefix": "IMG_OTP_ACCOUNT",
            "hook_id": "H_OTP_ACCOUNT",
            "proof_id": "proof_otp_account_warning",
            "headline": "Caller says delivery OTP. SMS app shows account change.",
            "ad_group": "otp_scam_warning",
            "proof": "screenshots/proof_otp_account_warning.png",
            "theme": "dark",
            "bg": "#08111F",
            "mode": "dark",
            "hook_type": "pain_led",
        },
        {
            "prefix": "IMG_OTP_INBOX",
            "hook_id": "H_OTP_INBOX",
            "proof_id": "proof_otp_inbox_focus",
            "headline": "Bank login SMS is buried. App finds the OTP.",
            "ad_group": "sms_organizer_volume",
            "proof": "screenshots/proof_otp_inbox_focus.png",
            "theme": "mint",
            "bg": "#F2FCF7",
            "mode": "light",
            "hook_type": "benefit_led",
        },
    ]
    rows: list[dict[str, str]] = []
    layouts: list[dict] = []
    for concept in concepts:
        for ratio, (spec, ratio_label, dims, width, height) in ratio_specs.items():
            asset_id = f"{concept['prefix']}_{ratio}"
            rows.append(
                {
                    "asset_id": asset_id,
                    "platform": "Google",
                    "campaign_type": "App Campaign",
                    "placement": "Auto",
                    "format": "image",
                    "ratio": ratio_label,
                    "dimensions": dims,
                    "persona": "app installer",
                    "ad_group": concept["ad_group"],
                    "hook_family": concept["theme"],
                    "hook": concept["headline"],
                    "hook_id": concept["hook_id"],
                    "hook_type": concept["hook_type"],
                    "hero_feature": concept["ad_group"],
                    "visual_proof": concept["proof_id"],
                    "proof_id": concept["proof_id"],
                    "primary_text": concept["headline"],
                    "headline": concept["headline"],
                    "description": "SMS Classifier helps review OTPs, links, and service texts in a clearer default SMS inbox.",
                    "cta": "",
                    "claim_risk": "low",
                    "status": "ready_for_eval",
                    "spec": spec,
                    "platform_overlays_app_name": "false",
                }
            )
            if ratio == "LANDSCAPE":
                if concept["prefix"] == "IMG_SCAM_PRIZE":
                    logo, head, ui = {"x": 5, "y": 7, "w": 35, "h": 10}, {"x": 5, "y": 24, "w": 40, "h": 34}, {"x": 52, "y": 8, "w": 43, "h": 84}
                elif concept["prefix"] == "IMG_OTP_ACCOUNT":
                    logo, head, ui = {"x": 54, "y": 7, "w": 36, "h": 10}, {"x": 54, "y": 24, "w": 39, "h": 34}, {"x": 6, "y": 8, "w": 43, "h": 84}
                else:
                    logo, head, ui = {"x": 6, "y": 7, "w": 33, "h": 10}, {"x": 6, "y": 20, "w": 35, "h": 36}, {"x": 48, "y": 9, "w": 47, "h": 82}
            elif ratio == "PORTRAIT":
                if concept["prefix"] == "IMG_OTP_ACCOUNT":
                    logo, head, ui = {"x": 7, "y": 5, "w": 42, "h": 7}, {"x": 7, "y": 70, "w": 80, "h": 14}, {"x": 10, "y": 16, "w": 80, "h": 50}
                elif concept["prefix"] == "IMG_OTP_INBOX":
                    logo, head, ui = {"x": 7, "y": 5, "w": 42, "h": 7}, {"x": 7, "y": 13, "w": 82, "h": 15}, {"x": 13, "y": 34, "w": 74, "h": 54}
                else:
                    logo, head, ui = {"x": 7, "y": 5, "w": 42, "h": 7}, {"x": 7, "y": 15, "w": 78, "h": 14}, {"x": 10, "y": 35, "w": 80, "h": 52}
            else:
                if concept["prefix"] == "IMG_OTP_ACCOUNT":
                    logo, head, ui = {"x": 7, "y": 6, "w": 38, "h": 8}, {"x": 9, "y": 68, "w": 82, "h": 16}, {"x": 18, "y": 18, "w": 64, "h": 45}
                elif concept["prefix"] == "IMG_OTP_INBOX":
                    logo, head, ui = {"x": 6, "y": 6, "w": 40, "h": 8}, {"x": 8, "y": 15, "w": 78, "h": 16}, {"x": 18, "y": 36, "w": 64, "h": 54}
                else:
                    logo, head, ui = {"x": 6, "y": 6, "w": 40, "h": 8}, {"x": 7, "y": 16, "w": 72, "h": 16}, {"x": 14, "y": 38, "w": 72, "h": 52}
            text_color = "#F8FAFC" if concept["mode"] == "dark" else "#102033"
            layouts.append(
                {
                    "asset_id": asset_id,
                    "spec": spec,
                    "canvas": {"width_px": width, "height_px": height},
                    "background_mode": concept["mode"],
                    "custom_background": concept["bg"],
                    "platform_overlays_app_name": False,
                    "elements": [
                        {
                            "type": "background",
                            "bbox_pct": {"x": 0, "y": 0, "w": 100, "h": 100},
                            "font_role": "none",
                            "color": concept["bg"],
                            "align": "stretch",
                        },
                        {"type": "logo", "bbox_pct": logo, "font_role": "logo", "align": "left", "show_name": True},
                        {
                            "type": "headline",
                            "bbox_pct": head,
                            "font_role": "hero",
                            "text": concept["headline"],
                            "color": text_color,
                            "align": "left",
                        },
                        {
                            "type": "product_ui",
                            "bbox_pct": ui,
                            "font_role": "none",
                            "src": concept["proof"],
                            "device_frame": True,
                            "shadow": True,
                            "corner_radius": 28,
                            "align": "center",
                        },
                    ],
                }
            )
    rows.append(
        {
            "asset_id": "VID_SCAM_PRIZE_9x16",
            "platform": "Google/YouTube",
            "campaign_type": "App Campaign Video",
            "placement": "Shorts/Reels style",
            "format": "video",
            "ratio": "9:16",
            "dimensions": "1080x1920",
            "persona": "app installer",
            "ad_group": "scam_sms_warning",
            "hook_family": "demo_proof_video",
            "hook": "Prize SMS says you won. App shows bank risk.",
            "hook_id": "H_SCAM_PRIZE",
            "hook_type": "pain_led",
            "hero_feature": "suspicious_link_warning",
            "visual_proof": "proof_scam_prize_warning",
            "proof_id": "proof_scam_prize_warning",
            "primary_text": "Prize SMS says you won. App shows bank risk.",
            "headline": "Prize SMS says you won. App shows bank risk.",
            "description": "A one-hook video showing the app warning, reason, and review payoff.",
            "cta": "",
            "claim_risk": "low",
            "status": "ready_for_eval",
            "spec": "google_app_video",
        }
    )
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with (RUN / "creative_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    dump_json("layout_specs.json", layouts)
    brand = load_brand_kit(RUN)
    for layout in layouts:
        image = render(layout, brand, background=layout["custom_background"])
        out = RUN / "assets" / f"{layout['asset_id']}_{layout['spec']}.png"
        image.save(out)
        image.save(RUN / "exports" / out.name)
    dump_yaml(
        "hierarchy_specs.yaml",
        {
            "assets": [
                {
                    "asset_id": row["asset_id"],
                    "first_second_focal_point": "headline plus large product UI proof",
                    "reading_order": ["brand lockup", "headline", "product UI proof"],
                    "proof_size_target": "40-55 percent of canvas with ad-scale proof text",
                    "brand_placement": "consistent visible lockup with real icon",
                }
                for row in rows
                if row["format"] == "image"
            ]
        },
    )
    copy_rows = [
        {
            "asset_id": row["asset_id"],
            "headline": row["headline"][:30],
            "long_headline": row["primary_text"][:90],
            "description": row["description"][:90],
            "cta": "Start 14-day trial",
        }
        for row in rows
        if row["format"] == "image"
    ]
    with (RUN / "copy_pack.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["asset_id", "headline", "long_headline", "description", "cta"])
        writer.writeheader()
        writer.writerows(copy_rows)
    write_text(
        "copy_pack.md",
        "# Text Asset Pack\n\n"
        + "\n".join(
            f"- {row['asset_id']}: {row['headline']} | {row['description']} | CTA: {row['cta']}"
            for row in copy_rows
        ),
    )
    write_text(
        "image_asset_briefs.md",
        """
# Image Asset Briefs

This v2 batch deliberately fixes the v1 critique:

- Real app icon and app name are present on every static image.
- Three visual systems are used: warm scam-link warning, dark OTP-account contradiction, and mint OTP-inbox organizer.
- In-phone proof text is rebuilt as ad-scale UI, not literal dense app screenshots.
- Every asset maps to one approved hook, one proof ID, and one claim boundary.
- No baked Install/Download CTA appears in the image; platform CTA should carry install action.
""",
    )
    dump_json(
        "image_prompts.json",
        {
            row["asset_id"]: "Deterministic app-install image with real app icon, ad-scale SMS Classifier UI proof, large headline, no generated text background."
            for row in rows
            if row["format"] == "image"
        },
    )


def write_video_files() -> None:
    dump_yaml(
        "storyboard.yaml",
        {
            "videos": [
                {
                    "asset_id": "VID_SCAM_PRIZE_9x16",
                    "hook_id": "H_SCAM_PRIZE",
                    "story_framework": "hook_story_offer",
                    "production_mode": "ui_led_slideshow",
                    "story_progression": "setup with product warning, reason reveal, payoff, CTA",
                    "beats": [
                        {
                            "proof_id": "proof_scam_prize_warning",
                            "screenshot": "screenshots/proof_scam_prize_warning.png",
                            "caption": "Prize SMS says you won. App shows bank risk.",
                            "hold_sec": 3.8,
                            "voiceover": "A prize-style SMS can push for bank details.",
                        },
                        {
                            "proof_id": "proof_scam_link_reason",
                            "screenshot": "screenshots/proof_scam_link_reason.png",
                            "caption": "Short link and bank details stay marked.",
                            "hold_sec": 3.8,
                            "voiceover": "SMS Classifier keeps the suspicious reason visible before you tap.",
                        },
                        {
                            "proof_id": "proof_scam_review_done",
                            "screenshot": "screenshots/proof_scam_review_done.png",
                            "caption": "Review the text before sharing details.",
                            "hold_sec": 3.8,
                            "voiceover": "You get a calmer moment to review the message first.",
                        },
                    ],
                    "outro": {"title": "SMS Classifier", "subtitle": "Open on Google Play", "hold_sec": 2.0},
                    "caption_typography": {"primary_px_target": 84, "secondary_px_target": 64},
                    "deterministic_layers": [
                        "product_ui_screenshots",
                        "captions",
                        "real_app_logo",
                        "voiceover",
                        "cta_outro",
                    ],
                    "rejection_notes": [
                        "No repeated static proof card",
                        "No settings/config proof beat",
                        "No fake OS warning",
                    ],
                }
            ]
        },
    )
    write_text(
        "storyboards.md",
        """
# Storyboards

## VID_SCAM_PRIZE_9x16

1. Prize-style SMS asks for bank details. The app warning is already visible in the first frame.
2. The reason screen shows short-link and bank-details context, so the story advances instead of repeating the same proof card.
3. The review state shows the warning remains visible before the user shares details.
4. End card: SMS Classifier, Open on Google Play.
""",
    )
    script = (
        "A prize-style text can push you toward bank details. SMS Classifier keeps the suspicious reason "
        "visible before you tap, so you get a calmer moment to review the message first."
    )
    write_text("video_scripts.md", f"# Video Scripts\n\n## VID_SCAM_PRIZE_9x16\n{script}")
    with (RUN / "voiceover_scripts.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["asset_id", "language", "voice", "speed", "script"])
        writer.writeheader()
        writer.writerow(
            {
                "asset_id": "VID_SCAM_PRIZE_9x16",
                "language": "en-IN",
                "voice": "indian_english",
                "speed": "0.94",
                "script": script,
            }
        )
    dump_json(
        "video_prompts.json",
        {
            "VID_SCAM_PRIZE_9x16": {
                "mode": "deterministic_ui_slideshow",
                "no_generative_broll": True,
                "rationale": "The critique called for a one-hook product-action video; deterministic UI is safer and clearer than generated phone footage.",
            }
        },
    )
    dump_json(
        "slideshow_scam_prize_9x16.json",
        {
            "canvas": {"width_px": 1080, "height_px": 1920},
            "fps": 30,
            "background_mode": "light",
            "crossfade_sec": 0.0,
            "motion": True,
            "asset_id": "VID_SCAM_PRIZE_9x16",
            "audio": "assets/audio/VID_SCAM_PRIZE_9x16.wav",
            "frames": [
                {
                    "image": "screenshots/proof_scam_prize_warning.png",
                    "caption": "Prize SMS says you won. App shows bank risk.",
                    "hold_sec": 3.8,
                    "bbox_pct": {"x": 14, "y": 20, "w": 72, "h": 61},
                    "proof_id": "proof_scam_prize_warning",
                },
                {
                    "image": "screenshots/proof_scam_link_reason.png",
                    "caption": "Short link and bank details stay marked.",
                    "hold_sec": 3.8,
                    "bbox_pct": {"x": 14, "y": 20, "w": 72, "h": 61},
                    "proof_id": "proof_scam_link_reason",
                },
                {
                    "image": "screenshots/proof_scam_review_done.png",
                    "caption": "Review the text before sharing details.",
                    "hold_sec": 3.8,
                    "bbox_pct": {"x": 14, "y": 20, "w": 72, "h": 61},
                    "proof_id": "proof_scam_review_done",
                },
            ],
            "outro": {"title": "SMS Classifier", "subtitle": "Open on Google Play", "hold_sec": 2.0},
            "proof_id": "proof_scam_prize_warning",
        },
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
        "chat",
        "bulk sms",
        "sms gateway",
        "sms marketing",
        "sms api",
        "sms sender",
        "otp api",
        "otp service",
        "email",
        "gmail",
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
        "send free sms",
        "fake sms",
        "anonymous",
        "template",
        "meaning",
        "definition",
        "examples",
    ]


def search_clusters() -> list[dict]:
    neg = shared_negatives()
    return [
        {
            "id": "sms_app_category_scale",
            "persona_id": "otp_searcher",
            "search_moment": "category_scale",
            "primary_query": "messages app",
            "keywords": [
                "messages app",
                "sms app",
                "sms message app",
                "text message app",
                "default sms app",
                "best messaging app for android",
                "messaging apps for android",
            ],
            "category_terms": ["messages app", "SMS app", "Android SMS app"],
            "primary_promise": "Android SMS app keeps OTPs, service texts, and review-needed messages easier to scan.",
            "claim_boundary": "Organization and review help only; does not guarantee perfect sorting or fraud prevention.",
            "estimated_monthly_searches": 37790,
            "priority": 1,
            "negative_keywords": neg,
            "landing_page_h1": "Messages App For Android",
            "landing_page_proof": [
                "OTP inbox and review-needed messages in one Android SMS app.",
                "Claim is limited to organization and review help.",
            ],
        },
        {
            "id": "spam_sms_problem_scale",
            "persona_id": "family_helper",
            "search_moment": "problem_aware_scale",
            "primary_query": "i keep getting spam texts",
            "keywords": ["i keep getting spam texts", "spam messages", "spam text messages", "spam sms", "spam sms messages", "sms filter"],
            "category_terms": ["spam SMS app", "SMS filter", "Android SMS app"],
            "primary_promise": "SMS app flags spam-looking texts so users can review before replying.",
            "claim_boundary": "Flags and review labels only; does not block every spam text or certify safety.",
            "estimated_monthly_searches": 26720,
            "priority": 2,
            "negative_keywords": neg,
            "landing_page_h1": "Spam SMS Review App",
            "landing_page_proof": ["Review spam-looking SMS in a calmer default inbox.", "Does not claim to block every spam message."],
        },
        {
            "id": "scam_text_problem_scale",
            "persona_id": "otp_fraud_worrier",
            "search_moment": "problem_aware_scale",
            "primary_query": "scam text messages",
            "keywords": [
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
            "category_terms": ["scam text app", "SMS warning app", "phishing SMS", "Android SMS app"],
            "primary_promise": "SMS app warns before suspicious-looking links or details requests are acted on.",
            "claim_boundary": "Shows warnings and review context; does not certify every text as safe or unsafe.",
            "estimated_monthly_searches": 23430,
            "priority": 3,
            "negative_keywords": neg,
            "landing_page_h1": "Scam Text Message Review",
            "landing_page_proof": ["SMS warning UI for suspicious-looking links and details requests.", "Claim is bounded to review context."],
        },
        {
            "id": "otp_utility_risk_scale",
            "persona_id": "otp_fraud_worrier",
            "search_moment": "otp_utility_and_risk",
            "primary_query": "otp app",
            "keywords": ["otp app", "otp scam", "otp sms", "bank otp", "otp fraud", "delivery otp scam", "otp scam warning app", "otp fraud warning app"],
            "category_terms": ["OTP app", "SMS app", "OTP warning app", "Android SMS app"],
            "primary_promise": "SMS app shows OTP context and helps users find bank codes faster.",
            "claim_boundary": "OTP context and organization only; does not guarantee fraud prevention.",
            "estimated_monthly_searches": 3450,
            "priority": 4,
            "negative_keywords": neg,
            "landing_page_h1": "OTP App For SMS Codes",
            "landing_page_proof": ["OTP inbox and review warning screens.", "No promise of guaranteed fraud prevention."],
        },
        {
            "id": "sms_organizer_control",
            "persona_id": "busy_otp_user",
            "search_moment": "solution_aware_control",
            "primary_query": "sms organizer",
            "keywords": ["sms organizer", "sms organizer app", "sms organiser app", "default sms app"],
            "category_terms": ["SMS organizer", "SMS app", "Android SMS app"],
            "primary_promise": "SMS app keeps OTPs and service messages easier to scan.",
            "claim_boundary": "Organization and review help only; does not guarantee perfect sorting or fraud prevention.",
            "estimated_monthly_searches": 1410,
            "priority": 5,
            "negative_keywords": neg,
            "landing_page_h1": "SMS Organizer",
            "landing_page_proof": ["OTP and service code organization in SMS Classifier.", "Bounded organization claim only."],
        },
        {
            "id": "sms_privacy_trust",
            "persona_id": "privacy_cautious_user",
            "search_moment": "trust_objection",
            "primary_query": "sms app privacy",
            "keywords": ["sms app privacy", "default sms permissions", "sms permissions android", "sms app data privacy"],
            "category_terms": ["SMS privacy", "Android SMS app", "default SMS app"],
            "primary_promise": "SMS app explains review features and data-control context clearly.",
            "claim_boundary": "Explain settings honestly; do not claim messages never leave device.",
            "estimated_monthly_searches": 0,
            "priority": 6,
            "negative_keywords": neg,
            "landing_page_h1": "SMS App Privacy",
            "landing_page_proof": ["Privacy and settings screens explain review feature controls.", "No absolute privacy claim."],
        },
    ]


def rsa(rsa_id: str, headlines: list[str], descriptions: list[str]) -> dict:
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


def write_search_files() -> None:
    clusters = search_clusters()
    dump_yaml(
        "keyword_clusters.yaml",
        {
            "market": "India",
            "language": "English",
            "brand_name": "SMS Classifier",
            "recommended_launch_match": "Exact and phrase first; broad and AI Max only after conversion tracking and search-term review are confirmed.",
            "volume_refresh": {
                "source": "keyword_planner_api_live_2026-06-27",
                "minimum_viable_volume_rule": "Launch clusters should have visible Keyword Planner metrics; zero-volume trust coverage is defensive only and should not be the spend driver.",
            },
            "clusters": clusters,
            "negative_keywords_initial": shared_negatives(),
        },
    )
    groups = [
        {
            "id": "sms_app_category_scale",
            "rsas": [
                rsa(
                    "sms_app_category_control",
                    [
                        "Messages App For Android",
                        "SMS App For OTPs",
                        "Android SMS App",
                        "Find OTPs In SMS",
                        "Cleaner Message Inbox",
                        "Default SMS Helper",
                        "Bank Codes Easier",
                        "Service Texts Organized",
                        "Review Risky Texts",
                        "Built For Indian SMS",
                        "OTP Inbox On Android",
                        "SMS Classifier App",
                    ],
                    [
                        "Use a default SMS inbox that groups OTPs, alerts, and review-needed texts.",
                        "Find login codes faster while keeping suspicious-looking messages visible.",
                        "For Android users in India who manage bank, delivery, and service texts.",
                        "Start a 14-day Pro trial; INR 199/year after the trial in India.",
                    ],
                ),
                rsa(
                    "sms_app_category_challenger",
                    [
                        "Text Message App",
                        "Organize Daily SMS",
                        "OTPs Easier To Find",
                        "Message Inbox Helper",
                        "Bank SMS In One Inbox",
                        "Review Texts Faster",
                        "Android Messages Aid",
                        "Service Alerts Sorted",
                        "Spot Suspicious Links",
                        "Made For Indian SMS",
                        "Codes And Alerts",
                        "Open On Google Play",
                    ],
                    [
                        "Use SMS Classifier as a clearer inbox for codes, alerts, and review moments.",
                        "See OTP and service messages without relying on a crowded default view.",
                        "Review suspicious-looking SMS while keeping everyday codes easy to find.",
                        "Trial lasts 14 days; Pro renews at INR 199/year in India.",
                    ],
                ),
            ],
        },
        {
            "id": "spam_sms_problem_scale",
            "rsas": [
                rsa(
                    "spam_sms_control",
                    [
                        "I Keep Getting Spam Texts",
                        "Spam Texts Keep Coming",
                        "SMS App Flags Spam",
                        "Review Spam-Looking SMS",
                        "Text Warning App",
                        "Odd Messages Highlighted",
                        "Spam SMS Review",
                        "Find Suspicious SMS",
                        "Calmer Text Inbox",
                        "Daily SMS Review",
                        "Default Inbox For SMS",
                        "SMS Classifier App",
                    ],
                    [
                        "Flags spam-looking SMS so you can review messages before replying.",
                        "Keeps suspicious-looking texts visible without claiming every text is unsafe.",
                        "Useful for OTPs, service alerts, spam texts, and daily Android SMS.",
                        "Start a 14-day Pro trial; INR 199/year after the trial in India.",
                    ],
                ),
                rsa(
                    "spam_sms_challenger",
                    [
                        "Spam Messages In Inbox",
                        "Review Odd SMS First",
                        "SMS Filter For Android",
                        "Spot Spam-Looking Texts",
                        "Text App With Warnings",
                        "SMS Review Helper",
                        "Less Message Clutter",
                        "Find Risky Texts",
                        "Spam SMS Warning",
                        "OTP And Spam Review",
                        "Indian SMS Helper",
                        "Open Play Listing",
                    ],
                    [
                        "See warning labels for spam-looking messages while you scan the inbox.",
                        "SMS Classifier helps review links, OTPs, and service messages together.",
                        "Does not promise to block every spam text; it surfaces review context.",
                        "Use the trial first, then Pro is INR 199/year in India.",
                    ],
                ),
            ],
        },
        {
            "id": "scam_text_problem_scale",
            "rsas": [
                rsa(
                    "scam_text_control",
                    [
                        "Scam Text Messages",
                        "SMS App Warns On Links",
                        "Smishing Text Review",
                        "Phishing SMS Warnings",
                        "Bank Details Warning",
                        "Review Suspicious Links",
                        "Text Scam Review App",
                        "SMS Fraud Warning",
                        "Spot Risky SMS Links",
                        "Android SMS Warnings",
                        "Scam SMS Review",
                        "SMS Classifier App",
                    ],
                    [
                        "Warns when an SMS link or details request looks suspicious.",
                        "Review phishing-style texts without claims that every message is unsafe.",
                        "Built for Android SMS moments involving OTPs, links, and service alerts.",
                        "Start a 14-day Pro trial; INR 199/year after the trial in India.",
                    ],
                ),
                rsa(
                    "scam_text_challenger",
                    [
                        "Text Scams In SMS",
                        "Phishing Text Alerts",
                        "Review Bank Detail Texts",
                        "SMS Warning App",
                        "Suspicious Link Review",
                        "Scam SMS Helper",
                        "Before You Tap A Link",
                        "Android Text Warnings",
                        "Smishing SMS Helper",
                        "Bank SMS Review",
                        "Link Risk Highlighted",
                        "Open On Google Play",
                    ],
                    [
                        "SMS Classifier keeps suspicious-looking link reasons visible for review.",
                        "Use a clearer SMS inbox before replying to details requests.",
                        "Warnings are review aids, not a guarantee that every text is risky or safe.",
                        "Try the Pro review features for 14 days before INR 199/year renewal.",
                    ],
                ),
            ],
        },
        {
            "id": "otp_utility_risk_scale",
            "rsas": [
                rsa(
                    "otp_utility_control",
                    [
                        "OTP App For SMS Codes",
                        "Bank OTP Finder",
                        "Delivery OTP Review",
                        "SMS Shows Code Context",
                        "Find Login Codes Fast",
                        "Review OTPs First",
                        "Account Code Warning",
                        "OTP Inbox On Android",
                        "Code Purpose Shown",
                        "Bank Codes In SMS",
                        "OTP SMS Organizer",
                        "SMS Classifier App",
                    ],
                    [
                        "Shows OTP context before you share a code under pressure.",
                        "Find bank login codes and review-needed OTPs inside the SMS inbox.",
                        "Helps with code review; it does not guarantee fraud prevention.",
                        "Start a 14-day Pro trial; INR 199/year after the trial in India.",
                    ],
                ),
                rsa(
                    "otp_utility_challenger",
                    [
                        "OTP Scam Warning App",
                        "OTP Fraud Review",
                        "SMS Code Review App",
                        "Account OTP Alert",
                        "Delivery Code Context",
                        "Bank Login Code Finder",
                        "Text App For OTPs",
                        "Find Recent OTPs",
                        "Review Codes In SMS",
                        "Default OTP Inbox",
                        "Indian OTP Helper",
                        "Open Play Listing",
                    ],
                    [
                        "Use SMS Classifier to see code context and recent OTPs faster.",
                        "Review delivery, bank, and account-code messages in one SMS app.",
                        "Warnings are bounded review labels, not a promise to stop every fraud.",
                        "Trial for 14 days; Pro is INR 199/year after that in India.",
                    ],
                ),
            ],
        },
        {
            "id": "sms_organizer_control",
            "rsas": [
                rsa(
                    "sms_organizer_control",
                    [
                        "SMS Organizer",
                        "SMS Organizer App",
                        "Android SMS Organizer",
                        "OTP Inbox Organizer",
                        "Bank Codes Organized",
                        "Find Login SMS Faster",
                        "Service Texts Sorted",
                        "Default SMS Helper",
                        "Cleaner Text Inbox",
                        "SMS App For Codes",
                        "Review Suspicious Texts",
                        "SMS Classifier App",
                    ],
                    [
                        "Shows codes, bank texts, and service alerts in a calmer default SMS inbox.",
                        "Keeps OTP and review-needed messages easier to scan during login.",
                        "Helpful for organization; it does not promise perfect sorting.",
                        "Start a 14-day Pro trial; INR 199/year after the trial in India.",
                    ],
                ),
                rsa(
                    "sms_organizer_challenger",
                    [
                        "Organize SMS Codes",
                        "OTP Messages Together",
                        "Text Inbox Organizer",
                        "Find Bank OTPs",
                        "Daily SMS Cleaner",
                        "Android Text Organizer",
                        "Service SMS Review",
                        "Codes Easier To Find",
                        "SMS Inbox Helper",
                        "Review Links Too",
                        "Default Text Helper",
                        "Open Google Play",
                    ],
                    [
                        "Keep OTPs and service texts easier to review in one Android SMS app.",
                        "A clearer inbox for login codes, delivery texts, and suspicious links.",
                        "Sorting and warnings are review aids, not absolute safety claims.",
                        "Use the trial first; Pro renews at INR 199/year in India.",
                    ],
                ),
            ],
        },
        {
            "id": "sms_privacy_trust",
            "rsas": [
                rsa(
                    "sms_privacy_control",
                    [
                        "SMS App Privacy",
                        "Default SMS Permissions",
                        "SMS Data Choices",
                        "Review App Settings",
                        "Android SMS Privacy",
                        "Privacy-Aware SMS App",
                        "Clear Trial Details",
                        "Review Feature Controls",
                        "Cloud Review Explained",
                        "SMS Permission Review",
                        "Data Choices Visible",
                        "SMS Classifier App",
                    ],
                    [
                        "Review app permissions, trial details, and feature controls before using Pro.",
                        "Explains review features without claiming every message stays on-device.",
                        "Use settings and Play listing details to understand data choices.",
                        "Start a 14-day Pro trial; INR 199/year after the trial in India.",
                    ],
                ),
                rsa(
                    "sms_privacy_challenger",
                    [
                        "SMS Permissions Android",
                        "Default Text App Privacy",
                        "Review SMS Settings",
                        "Data Control Context",
                        "Clear Pro Trial Terms",
                        "Android Text Privacy",
                        "Feature Controls Visible",
                        "SMS Review Settings",
                        "Privacy Info For SMS",
                        "Review Before Pro",
                        "Open Play Listing",
                        "SMS Classifier",
                    ],
                    [
                        "SMS Classifier keeps privacy and Pro review settings visible for checking.",
                        "See the Play listing and app controls before enabling review features.",
                        "No absolute privacy claim; cloud review features are described honestly.",
                        "Trial lasts 14 days, then Pro is INR 199/year in India.",
                    ],
                ),
            ],
        },
    ]
    dump_yaml(
        "google_search_copy.yaml",
        {
            "metadata": {
                "product": "SMS Classifier",
                "campaign_type": "Google Search RSA",
                "status": "v2_production_candidate_high_volume",
                "dynamic_copy_plan": "Static RSAs first; DKI only after search terms and negatives are reviewed.",
                "ai_max_guardrail": "Review any generated assets against claim boundaries.",
            },
            "brand_name": "SMS Classifier",
            "require_brand_ad_group": False,
            "require_trust_ad_group": True,
            "ad_groups": groups,
        },
    )
    dump_yaml(
        "search_intent_map.yaml",
        {
            "intents": [
                {
                    "ad_group_id": cluster["id"],
                    "persona_id": cluster["persona_id"],
                    "search_moment": cluster["search_moment"],
                    "primary_query": cluster["primary_query"],
                    "desired_outcome": cluster["primary_promise"],
                    "claim_boundary": cluster["claim_boundary"],
                    "estimated_monthly_searches": cluster["estimated_monthly_searches"],
                }
                for cluster in clusters
            ]
        },
    )
    dump_yaml(
        "keyword_seed_map.yaml",
        {
            "market": "India",
            "language": "English",
            "geo_target": "geoTargetConstants/2356",
            "language_id": "languageConstants/1000",
            "seed_source": "prior live Keyword Planner API expansion from 2026-06-27",
            "seeds": [
                "messages app",
                "sms app",
                "spam texts",
                "scam text messages",
                "otp app",
                "sms organizer",
                "sms app privacy",
            ],
        },
    )


def write_quality_notes() -> None:
    write_text(
        "CREATIVE_CRITIQUE_FIXES.md",
        """
# Creative Critique Fixes

This v2 run is built against the Codex + Claude critique of v1.

| V1 critique | V2 fix | Evidence |
|---|---|---|
| Blank logo placeholder | Real app icon copied to `inputs/logo-primary.png`; every static layout has a logo lockup. | `brand_kit.yaml`, `layout_specs.json` |
| Static set was homogeneous | Three concept systems: warm scam-link warning, dark OTP-account contradiction, and mint OTP-inbox organizer. | `creative_matrix.csv`, rendered assets |
| Synthetic proof was too dense/tiny | Rebuilt ad-scale proof screenshots with 2 visible rows, 52px+ important text, and <=3 proof text blocks. | `screenshots/`, `proof_specs.yaml` |
| Video was mostly one repeated static card | Video uses 3 distinct proof screens and captions that advance setup -> reason -> payoff. | `storyboard.yaml`, `slideshow_scam_prize_9x16.json` |
| Video VO/caption parity was weak | VO adds context and does not simply read captions. | `voiceover_scripts.csv` |
| Search plan was stale/low-volume | New Search pack uses the high-volume Keyword Planner source and two RSAs per launch group. | `keyword_research.csv`, `keyword_clusters.yaml`, `google_search_copy.yaml` |
| Publish set not tied to eval | `exports/launch_ready` should be populated only after eval decisions are `ship`. | `launch_ready_assets.csv` after eval |
""",
    )
    write_text(
        "SEARCH_PLAN_PARITY.md",
        """
# Search Plan Parity Note

Do not enable the old paused Search campaign as the main launch plan.

The v1 Google Ads account contains an earlier paused low-volume Search campaign. This v2 folder is the source of truth for the next Search publish candidate. It uses the same-day high-volume Keyword Planner data and a two-RSA-per-group copy structure.

Before any Google Ads mutate/publish step, compare the campaign plan fingerprint against:

- `keyword_clusters.yaml`
- `google_search_copy.yaml`
- `search_copy_eval_results.json`

No Search campaign should be enabled unless the plan matches these evaluated artifacts and the user has explicitly approved serving/spend.
""",
    )
    write_text(
        "user_validation_doc.md",
        """
# User Validation Doc

Please confirm before serving spend:

1. SMS Classifier Pro trial remains 14 days and Pro remains INR 199/year in India.
2. The app icon in `inputs/logo-primary.png` is the approved current icon.
3. The safer claim boundary is acceptable: helps flag/review suspicious-looking SMS, without promising prevention.
4. The v2 assets should supersede v1; v1 should remain paused only.
""",
    )
    write_text("client_summary.md", "# Client Summary\n\nPending eval. This file will be refreshed after copy/search/creative gates run.")


def make_contact_sheet() -> None:
    paths = sorted((RUN / "assets").glob("IMG_*.png"))
    if not paths:
        return
    sheet = Image.new("RGB", (3 * 340 + 30, ((len(paths) + 2) // 3) * 360 + 30), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((300, 300), Image.LANCZOS)
        x = 20 + (idx % 3) * 340
        y = 20 + (idx // 3) * 360
        bg = Image.new("RGB", (300, 300), "#F5F5F5")
        bg.paste(image, ((300 - image.width) // 2, (300 - image.height) // 2))
        sheet.paste(bg, (x, y))
        draw.text((x, y + 308), path.name[:42], fill=(0, 0, 0), font=font(14))
    sheet.save(RUN / "evals/codex_review/v2_static_contact_sheet.jpg", quality=92)


def main() -> int:
    make_dirs()
    logo = seed_logo()
    copy_keyword_sources()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    write_brand_kit()
    write_core_docs(now)
    write_strategy_files()
    write_screens_and_proofs(now, logo)
    write_creative_matrix_and_render()
    write_video_files()
    write_search_files()
    write_quality_notes()
    make_contact_sheet()
    print(RUN)
    print(f"logo_hash={file_sha256(logo)}")
    print(f"static_assets={len(list((RUN / 'assets').glob('IMG_*.png')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
