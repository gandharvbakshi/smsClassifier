from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml
from google.protobuf.field_mask_pb2 import FieldMask


ROOT = Path(__file__).resolve().parents[2]
CENTRAL = Path(r"D:\Projects\ad creatives")
RUN = ROOT / "ads" / "2026-08-10-sms-classifier-search-recovery-v9"
PLAN_PATH = RUN / "search_recovery_action_plan.yaml"
COPY_PATH = RUN / "google_search_copy.yaml"
EVAL_PATH = RUN / "search_copy_eval_results.json"
DRY_RUN_PATH = RUN / "search_recovery_validate_only.json"
BEFORE_PATH = RUN / "search_recovery_before_live.json"
LIVE_PATH = RUN / "search_recovery_live_readback.json"
ROLLBACK_PATH = RUN / "search_recovery_rollback_readback.json"
CUSTOMER_ID = "6269702350"
CAMPAIGN_ID = "23973905019"
CAMPAIGN_RESOURCE = f"customers/{CUSTOMER_ID}/campaigns/{CAMPAIGN_ID}"

sys.path.insert(0, str(CENTRAL))

from adengine.config import load_env  # noqa: E402
from adengine.google_ads import _load_client  # noqa: E402


def enum_name(value) -> str:
    return str(getattr(value, "name", "") or value)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def canonical_text_bytes(path: Path) -> bytes:
    return path.read_text(encoding="utf-8").encode("utf-8")


def gaql(client, query: str):
    return list(client.get_service("GoogleAdsService").search(customer_id=CUSTOMER_ID, query=query))


def load_plan() -> dict:
    plan = yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8"))
    search_copy = yaml.safe_load(COPY_PATH.read_text(encoding="utf-8"))
    evaluation = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    if evaluation.get("decision") != "pass" or not evaluation.get("model_reviews"):
        raise RuntimeError("Reviewed Search copy must pass deterministic and required model evaluation.")
    if any(
        str(review.get("verdict") or "").lower() == "reject" or review.get("hard_fails")
        for review in evaluation["model_reviews"].values()
    ):
        raise RuntimeError("A required Search model critic rejected the reviewed copy.")
    expected_copy_hash = (evaluation.get("source_hashes") or {}).get("google_search_copy.yaml")
    if expected_copy_hash != hashlib.sha256(canonical_text_bytes(COPY_PATH)).hexdigest():
        raise RuntimeError("Search copy changed after evaluation; rerun the review gate.")
    copy_groups = {group["id"]: group for group in search_copy.get("ad_groups") or []}
    metadata = plan["metadata"]
    if str(metadata["customer_id"]) != CUSTOMER_ID or str(metadata["campaign_id"]) != CAMPAIGN_ID:
        raise RuntimeError("Plan binding does not match the protected customer and campaign.")
    if int(metadata["fixed_daily_budget_micros"]) != 20_000_000:
        raise RuntimeError("The bounded recovery must keep the Search budget at INR 20/day.")
    if int(metadata["target_cpc_ceiling_micros"]) != 18_000_000:
        raise RuntimeError("Unexpected target CPC ceiling.")
    groups = plan.get("ad_groups") or []
    if len(groups) != 2:
        raise RuntimeError("The bounded recovery requires exactly two existing ad groups.")
    for group in groups:
        if len(group.get("keywords") or []) not in range(1, 7):
            raise RuntimeError(f"Unexpected keyword count for {group['id']}.")
        keys = {(item["text"].strip().lower(), item["match_type"]) for item in group["keywords"]}
        if len(keys) != len(group["keywords"]):
            raise RuntimeError(f"Duplicate planned keyword in {group['id']}.")
        if any(match not in {"EXACT", "PHRASE"} for _, match in keys):
            raise RuntimeError("Broad match is forbidden.")
        source_group = copy_groups.get(group["id"])
        if not source_group:
            raise RuntimeError(f"Search copy group is missing for {group['id']}.")
        source_rsas = {rsa["id"]: rsa for rsa in source_group.get("rsas") or []}
        rsa_ids = group.get("rsa_ids") or []
        if len(rsa_ids) != 2 or len(set(rsa_ids)) != 2:
            raise RuntimeError(f"Exactly two distinct recovery RSAs are required for {group['id']}.")
        group["rsas"] = []
        for rsa_id in rsa_ids:
            source = source_rsas.get(rsa_id)
            if not source:
                raise RuntimeError(f"RSA {rsa_id} is missing from the reviewed Search copy pack.")
            rsa = {
                "id": rsa_id,
                "paths": source["paths"],
                "headlines": [item["text"] for item in source["headlines"]],
                "descriptions": [item["text"] for item in source["descriptions"]],
            }
            if len(rsa["headlines"]) != 15 or len(rsa["descriptions"]) != 4:
                raise RuntimeError(f"RSA asset count is invalid for {rsa_id}.")
            if any(len(text) > 30 for text in rsa["headlines"]):
                raise RuntimeError(f"RSA headline exceeds 30 chars for {rsa_id}.")
            if any(len(text) > 90 for text in rsa["descriptions"]):
                raise RuntimeError(f"RSA description exceeds 90 chars for {rsa_id}.")
            group["rsas"].append(rsa)
    return plan


def plan_hash() -> str:
    digest = hashlib.sha256()
    digest.update(canonical_text_bytes(PLAN_PATH))
    digest.update(canonical_text_bytes(COPY_PATH))
    return digest.hexdigest()


def campaign_state(client) -> dict:
    rows = gaql(
        client,
        f"""
        SELECT campaign.id, campaign.name, campaign.status, campaign.serving_status,
          campaign.primary_status, campaign.primary_status_reasons,
          campaign.bidding_strategy_type, campaign.target_spend.cpc_bid_ceiling_micros,
          campaign.campaign_budget, campaign_budget.amount_micros,
          campaign.network_settings.target_google_search,
          campaign.network_settings.target_search_network,
          campaign.network_settings.target_content_network,
          campaign.network_settings.target_partner_search_network
        FROM campaign
        WHERE campaign.id = {CAMPAIGN_ID}
        """,
    )
    if len(rows) != 1:
        raise RuntimeError(f"Expected one campaign, found {len(rows)}.")
    row = rows[0]
    network = row.campaign.network_settings
    return {
        "id": str(row.campaign.id),
        "name": row.campaign.name,
        "status": enum_name(row.campaign.status),
        "serving_status": enum_name(row.campaign.serving_status),
        "primary_status": enum_name(row.campaign.primary_status),
        "primary_status_reasons": [enum_name(value) for value in row.campaign.primary_status_reasons],
        "bidding_strategy_type": enum_name(row.campaign.bidding_strategy_type),
        "cpc_bid_ceiling_micros": int(row.campaign.target_spend.cpc_bid_ceiling_micros or 0),
        "budget_resource": row.campaign.campaign_budget,
        "budget_amount_micros": int(row.campaign_budget.amount_micros),
        "networks": {
            "google_search": bool(network.target_google_search),
            "search_network": bool(network.target_search_network),
            "content_network": bool(network.target_content_network),
            "partner_search_network": bool(network.target_partner_search_network),
        },
    }


def targeting_state(client) -> dict:
    locations = gaql(
        client,
        f"""
        SELECT campaign_criterion.resource_name, campaign_criterion.status,
          campaign_criterion.negative, campaign_criterion.location.geo_target_constant
        FROM campaign_criterion
        WHERE campaign.id = {CAMPAIGN_ID}
          AND campaign_criterion.type = LOCATION
          AND campaign_criterion.status != REMOVED
        """,
    )
    languages = gaql(
        client,
        f"""
        SELECT campaign_criterion.resource_name, campaign_criterion.status,
          campaign_criterion.language.language_constant
        FROM campaign_criterion
        WHERE campaign.id = {CAMPAIGN_ID}
          AND campaign_criterion.type = LANGUAGE
          AND campaign_criterion.status != REMOVED
        """,
    )
    return {
        "locations": sorted(
            [
            {
                "resource_name": row.campaign_criterion.resource_name,
                "status": enum_name(row.campaign_criterion.status),
                "negative": bool(row.campaign_criterion.negative),
                "geo_target_constant": row.campaign_criterion.location.geo_target_constant,
            }
            for row in locations
            ],
            key=lambda item: item["resource_name"],
        ),
        "languages": sorted(
            [
            {
                "resource_name": row.campaign_criterion.resource_name,
                "status": enum_name(row.campaign_criterion.status),
                "language_constant": row.campaign_criterion.language.language_constant,
            }
            for row in languages
            ],
            key=lambda item: item["resource_name"],
        ),
    }


def negative_keyword_state(client) -> list[dict]:
    rows = gaql(
        client,
        f"""
        SELECT campaign_criterion.resource_name, campaign_criterion.status,
          campaign_criterion.keyword.text, campaign_criterion.keyword.match_type
        FROM campaign_criterion
        WHERE campaign.id = {CAMPAIGN_ID}
          AND campaign_criterion.type = KEYWORD
          AND campaign_criterion.negative = TRUE
          AND campaign_criterion.status != REMOVED
        """,
    )
    return sorted(
        [
            {
                "resource_name": row.campaign_criterion.resource_name,
                "status": enum_name(row.campaign_criterion.status),
                "text": row.campaign_criterion.keyword.text,
                "match_type": enum_name(row.campaign_criterion.keyword.match_type),
            }
            for row in rows
        ],
        key=lambda item: (item["text"].lower(), item["match_type"], item["resource_name"]),
    )


def ad_group_state(client, group_id: str) -> dict:
    rows = gaql(
        client,
        f"""
        SELECT ad_group.id, ad_group.name, ad_group.resource_name, ad_group.status,
          ad_group.primary_status, ad_group.primary_status_reasons
        FROM ad_group WHERE ad_group.id = {group_id}
        """,
    )
    if len(rows) != 1:
        raise RuntimeError(f"Expected one ad group {group_id}, found {len(rows)}.")
    row = rows[0]
    return {
        "id": str(row.ad_group.id),
        "name": row.ad_group.name,
        "resource_name": row.ad_group.resource_name,
        "status": enum_name(row.ad_group.status),
        "primary_status": enum_name(row.ad_group.primary_status),
        "primary_status_reasons": [enum_name(value) for value in row.ad_group.primary_status_reasons],
    }


def keyword_state(client, group_id: str) -> list[dict]:
    rows = gaql(
        client,
        f"""
        SELECT ad_group_criterion.resource_name, ad_group_criterion.status,
          ad_group_criterion.primary_status, ad_group_criterion.primary_status_reasons,
          ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type
        FROM ad_group_criterion
        WHERE ad_group.id = {group_id}
          AND ad_group_criterion.type = KEYWORD
          AND ad_group_criterion.negative = FALSE
          AND ad_group_criterion.status != REMOVED
        """,
    )
    return sorted(
        [
            {
                "resource_name": row.ad_group_criterion.resource_name,
                "status": enum_name(row.ad_group_criterion.status),
                "primary_status": enum_name(row.ad_group_criterion.primary_status),
                "primary_status_reasons": [enum_name(v) for v in row.ad_group_criterion.primary_status_reasons],
                "text": row.ad_group_criterion.keyword.text,
                "match_type": enum_name(row.ad_group_criterion.keyword.match_type),
            }
            for row in rows
        ],
        key=lambda item: (item["text"].lower(), item["match_type"]),
    )


def rsa_state(client, group_id: str) -> list[dict]:
    rows = gaql(
        client,
        f"""
        SELECT ad_group_ad.resource_name, ad_group_ad.status, ad_group_ad.primary_status,
          ad_group_ad.primary_status_reasons, ad_group_ad.ad_strength,
          ad_group_ad.policy_summary.approval_status, ad_group_ad.policy_summary.review_status,
          ad_group_ad.ad.final_urls, ad_group_ad.ad.responsive_search_ad.headlines,
          ad_group_ad.ad.responsive_search_ad.descriptions,
          ad_group_ad.ad.responsive_search_ad.path1, ad_group_ad.ad.responsive_search_ad.path2
        FROM ad_group_ad
        WHERE ad_group.id = {group_id}
          AND ad_group_ad.ad.type = RESPONSIVE_SEARCH_AD
          AND ad_group_ad.status != REMOVED
        """,
    )
    return [
        {
            "resource_name": row.ad_group_ad.resource_name,
            "status": enum_name(row.ad_group_ad.status),
            "primary_status": enum_name(row.ad_group_ad.primary_status),
            "primary_status_reasons": [enum_name(v) for v in row.ad_group_ad.primary_status_reasons],
            "ad_strength": enum_name(row.ad_group_ad.ad_strength),
            "approval_status": enum_name(row.ad_group_ad.policy_summary.approval_status),
            "review_status": enum_name(row.ad_group_ad.policy_summary.review_status),
            "final_urls": list(row.ad_group_ad.ad.final_urls),
            "headlines": [asset.text for asset in row.ad_group_ad.ad.responsive_search_ad.headlines],
            "descriptions": [asset.text for asset in row.ad_group_ad.ad.responsive_search_ad.descriptions],
            "path1": row.ad_group_ad.ad.responsive_search_ad.path1,
            "path2": row.ad_group_ad.ad.responsive_search_ad.path2,
        }
        for row in rows
    ]


def rsa_signature(row: dict) -> tuple:
    return (
        tuple(sorted(row["headlines"])),
        tuple(sorted(row["descriptions"])),
        row["path1"],
        row["path2"],
        tuple(row["final_urls"]),
    )


def planned_rsa_signature(rsa: dict, final_url: str) -> tuple:
    return (
        tuple(sorted(rsa["headlines"])),
        tuple(sorted(rsa["descriptions"])),
        rsa["paths"]["path1"],
        rsa["paths"]["path2"],
        (final_url,),
    )


def account_snapshot(client, plan: dict) -> dict:
    return {
        "captured_at": utc_now(),
        "campaign": campaign_state(client),
        "targeting": targeting_state(client),
        "campaign_negative_keywords": negative_keyword_state(client),
        "ad_groups": {
            group["id"]: {
                "ad_group": ad_group_state(client, group["ad_group_id"]),
                "keywords": keyword_state(client, group["ad_group_id"]),
                "rsas": rsa_state(client, group["ad_group_id"]),
            }
            for group in plan["ad_groups"]
        },
    }


def assert_protected_before(snapshot: dict, plan: dict, allow_applied: bool = False) -> None:
    campaign = snapshot["campaign"]
    expected_cpc = int(
        plan["metadata"]["target_cpc_ceiling_micros"]
        if allow_applied
        else plan["metadata"]["current_cpc_ceiling_micros"]
    )
    checks = {
        "campaign_enabled": campaign["status"] == "ENABLED",
        "campaign_eligible": campaign["primary_status"] == "ELIGIBLE",
        "maximize_clicks": campaign["bidding_strategy_type"] == "TARGET_SPEND",
        "cpc_expected": campaign["cpc_bid_ceiling_micros"] == expected_cpc,
        "budget_fixed": campaign["budget_amount_micros"] == int(plan["metadata"]["fixed_daily_budget_micros"]),
        "google_search_only": campaign["networks"] == {
            "google_search": True,
            "search_network": False,
            "content_network": False,
            "partner_search_network": False,
        },
        "india_only": [item["geo_target_constant"] for item in snapshot["targeting"]["locations"] if not item["negative"]] == ["geoTargetConstants/2356"],
        "english_only": [item["language_constant"] for item in snapshot["targeting"]["languages"]] == ["languageConstants/1000"],
        "groups_enabled": all(item["ad_group"]["status"] == "ENABLED" for item in snapshot["ad_groups"].values()),
    }
    if not all(checks.values()):
        raise RuntimeError(f"Protected precondition failed: {checks}")


def build_operations(client, plan: dict, snapshot: dict) -> tuple[list, list, list, object]:
    keyword_ops = []
    rsa_ops = []
    pause_old_ops = []
    final_url = plan["metadata"]["final_url"]
    for group in plan["ad_groups"]:
        current = snapshot["ad_groups"][group["id"]]
        existing_keywords = {(item["text"].lower(), item["match_type"]) for item in current["keywords"]}
        existing_rsas = {rsa_signature(item) for item in current["rsas"]}
        if any(planned_rsa_signature(rsa, final_url) in existing_rsas for rsa in group["rsas"]):
            raise RuntimeError(f"A planned RSA already exists in {group['id']}; use live readback for idempotent verification.")
        pause_rows = [item for item in current["rsas"] if item["resource_name"] == group["pause_ad_resource"]]
        if len(pause_rows) != 1 or pause_rows[0]["status"] != "ENABLED" or pause_rows[0]["ad_strength"] != "POOR":
            raise RuntimeError(f"The reviewed poor-strength RSA is not safely displaceable in {group['id']}: {pause_rows}")
        group_resource = current["ad_group"]["resource_name"]
        for keyword in group["keywords"]:
            key = (keyword["text"].lower(), keyword["match_type"])
            if key in existing_keywords:
                raise RuntimeError(f"Planned keyword already exists: {group['id']} {key}")
            operation = client.get_type("AdGroupCriterionOperation")
            criterion = operation.create
            criterion.ad_group = group_resource
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.keyword.text = keyword["text"]
            criterion.keyword.match_type = getattr(client.enums.KeywordMatchTypeEnum, keyword["match_type"])
            keyword_ops.append(operation)

        for rsa in group["rsas"]:
            operation = client.get_type("AdGroupAdOperation")
            ad_group_ad = operation.create
            ad_group_ad.ad_group = group_resource
            ad_group_ad.status = client.enums.AdGroupAdStatusEnum.PAUSED
            ad_group_ad.ad.final_urls.append(final_url)
            search_ad = ad_group_ad.ad.responsive_search_ad
            search_ad.path1 = rsa["paths"]["path1"]
            search_ad.path2 = rsa["paths"]["path2"]
            for text in rsa["headlines"]:
                asset = client.get_type("AdTextAsset")
                asset.text = text
                search_ad.headlines.append(asset)
            for text in rsa["descriptions"]:
                asset = client.get_type("AdTextAsset")
                asset.text = text
                search_ad.descriptions.append(asset)
            rsa_ops.append(operation)

        operation = client.get_type("AdGroupAdOperation")
        operation.update.resource_name = group["pause_ad_resource"]
        operation.update.status = client.enums.AdGroupAdStatusEnum.PAUSED
        operation.update_mask.CopyFrom(FieldMask(paths=["status"]))
        pause_old_ops.append(operation)

    campaign_op = client.get_type("CampaignOperation")
    campaign_op.update.resource_name = CAMPAIGN_RESOURCE
    campaign_op.update.target_spend.cpc_bid_ceiling_micros = int(plan["metadata"]["target_cpc_ceiling_micros"])
    campaign_op.update_mask.CopyFrom(FieldMask(paths=["target_spend.cpc_bid_ceiling_micros"]))
    return keyword_ops, rsa_ops, pause_old_ops, campaign_op


def validate_only(client, keyword_ops: list, rsa_ops: list, pause_old_ops: list, campaign_op) -> None:
    keyword_request = client.get_type("MutateAdGroupCriteriaRequest")
    keyword_request.customer_id = CUSTOMER_ID
    keyword_request.operations.extend(keyword_ops)
    keyword_request.validate_only = True
    client.get_service("AdGroupCriterionService").mutate_ad_group_criteria(request=keyword_request)

    rsa_request = client.get_type("MutateAdGroupAdsRequest")
    rsa_request.customer_id = CUSTOMER_ID
    rsa_request.operations.extend(rsa_ops)
    rsa_request.validate_only = True
    client.get_service("AdGroupAdService").mutate_ad_group_ads(request=rsa_request)

    pause_request = client.get_type("MutateAdGroupAdsRequest")
    pause_request.customer_id = CUSTOMER_ID
    pause_request.operations.extend(pause_old_ops)
    pause_request.validate_only = True
    client.get_service("AdGroupAdService").mutate_ad_group_ads(request=pause_request)

    campaign_request = client.get_type("MutateCampaignsRequest")
    campaign_request.customer_id = CUSTOMER_ID
    campaign_request.operations.append(campaign_op)
    campaign_request.validate_only = True
    client.get_service("CampaignService").mutate_campaigns(request=campaign_request)


def set_campaign_cpc(client, micros: int) -> None:
    operation = client.get_type("CampaignOperation")
    operation.update.resource_name = CAMPAIGN_RESOURCE
    operation.update.target_spend.cpc_bid_ceiling_micros = micros
    operation.update_mask.CopyFrom(FieldMask(paths=["target_spend.cpc_bid_ceiling_micros"]))
    client.get_service("CampaignService").mutate_campaigns(customer_id=CUSTOMER_ID, operations=[operation])


def set_ad_statuses(client, resources: list[str], status: str) -> list[str]:
    if not resources:
        return []
    operations = []
    for resource in resources:
        operation = client.get_type("AdGroupAdOperation")
        operation.update.resource_name = resource
        operation.update.status = getattr(client.enums.AdGroupAdStatusEnum, status)
        operation.update_mask.CopyFrom(FieldMask(paths=["status"]))
        operations.append(operation)
    response = client.get_service("AdGroupAdService").mutate_ad_group_ads(
        customer_id=CUSTOMER_ID, operations=operations
    )
    return [item.resource_name for item in response.results]


def pause_resources(client, keyword_resources: list[str], ad_resources: list[str]) -> dict:
    result = {"keywords": [], "ads": []}
    if keyword_resources:
        operations = []
        for resource in keyword_resources:
            operation = client.get_type("AdGroupCriterionOperation")
            operation.update.resource_name = resource
            operation.update.status = client.enums.AdGroupCriterionStatusEnum.PAUSED
            operation.update_mask.CopyFrom(FieldMask(paths=["status"]))
            operations.append(operation)
        response = client.get_service("AdGroupCriterionService").mutate_ad_group_criteria(
            customer_id=CUSTOMER_ID, operations=operations
        )
        result["keywords"] = [item.resource_name for item in response.results]
    result["ads"] = set_ad_statuses(client, ad_resources, "PAUSED")
    return result


def verify_after(client, plan: dict, before: dict, resources: dict) -> dict:
    after = account_snapshot(client, plan)
    assert_protected_before(after, plan, allow_applied=True)
    protected_checks = {
        "budget_unchanged": after["campaign"]["budget_amount_micros"] == before["campaign"]["budget_amount_micros"],
        "budget_resource_unchanged": after["campaign"]["budget_resource"] == before["campaign"]["budget_resource"],
        "networks_unchanged": after["campaign"]["networks"] == before["campaign"]["networks"],
        "targeting_unchanged": after["targeting"] == before["targeting"],
        "campaign_negatives_unchanged": after["campaign_negative_keywords"] == before["campaign_negative_keywords"],
        "ad_groups_unchanged": all(
            after["ad_groups"][key]["ad_group"] == before["ad_groups"][key]["ad_group"]
            for key in before["ad_groups"]
        ),
        "cpc_ceiling_updated": after["campaign"]["cpc_bid_ceiling_micros"] == int(plan["metadata"]["target_cpc_ceiling_micros"]),
    }
    keyword_resources = set(resources["created_keyword_resources"])
    ad_resources = set(resources["created_ad_resources"])
    read_keyword_resources = {
        item["resource_name"] for group in after["ad_groups"].values() for item in group["keywords"]
    }
    read_ad_resources = {item["resource_name"] for group in after["ad_groups"].values() for item in group["rsas"]}
    protected_checks["created_keywords_read_back"] = keyword_resources <= read_keyword_resources
    protected_checks["created_ads_read_back"] = ad_resources <= read_ad_resources
    ad_status_by_resource = {
        item["resource_name"]: item["status"]
        for group in after["ad_groups"].values()
        for item in group["rsas"]
    }
    protected_checks["created_ads_enabled"] = all(
        ad_status_by_resource.get(resource) == "ENABLED" for resource in ad_resources
    )
    protected_checks["displaced_poor_ads_paused"] = all(
        ad_status_by_resource.get(resource) == "PAUSED"
        for resource in resources.get("paused_old_ad_resources") or []
    )
    if not all(protected_checks.values()):
        raise RuntimeError(f"Post-apply verification failed: {protected_checks}")
    return {"snapshot": after, "checks": protected_checks}


def rollback(client, plan: dict, evidence: dict) -> dict:
    if evidence.get("plan_hash") != plan_hash():
        raise RuntimeError("Current plan hash differs from live evidence; refusing rollback.")
    resources = evidence["changes"]
    paused = pause_resources(
        client,
        resources.get("created_keyword_resources") or [],
        resources.get("created_ad_resources") or [],
    )
    restored_old_ads = set_ad_statuses(
        client, resources.get("paused_old_ad_resources") or [], "ENABLED"
    )
    set_campaign_cpc(client, int(plan["metadata"]["current_cpc_ceiling_micros"]))
    snapshot = account_snapshot(client, plan)
    assert_protected_before(snapshot, plan, allow_applied=False)
    result = {
        "mode": "rollback",
        "rolled_back_at": utc_now(),
        "plan_hash": plan_hash(),
        "paused_resources": paused,
        "restored_old_ad_resources": restored_old_ads,
        "snapshot": snapshot,
    }
    write_json_atomic(ROLLBACK_PATH, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate, apply, or roll back bounded SMS Classifier Search recovery.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--confirm-customer-id", default="")
    args = parser.parse_args()
    if args.apply and args.rollback:
        raise RuntimeError("Choose either --apply or --rollback.")
    if (args.apply or args.rollback) and args.confirm_customer_id != CUSTOMER_ID:
        raise RuntimeError(f"Live mutation requires --confirm-customer-id {CUSTOMER_ID}.")

    plan = load_plan()
    load_env()
    client = _load_client()

    if args.rollback:
        if not LIVE_PATH.exists():
            raise RuntimeError("Live evidence is required for rollback.")
        result = rollback(client, plan, json.loads(LIVE_PATH.read_text(encoding="utf-8")))
        print(ROLLBACK_PATH)
        print(f"Rollback complete: {len(result['paused_resources']['keywords'])} keywords and {len(result['paused_resources']['ads'])} ads paused; CPC ceiling restored.")
        return 0

    if args.apply and LIVE_PATH.exists():
        evidence = json.loads(LIVE_PATH.read_text(encoding="utf-8"))
        if evidence.get("plan_hash") == plan_hash() and evidence.get("mode") == "apply":
            verified = verify_after(client, plan, evidence["before"], evidence["changes"])
            print(LIVE_PATH)
            print(f"No-op: existing live recovery reverified with checks={verified['checks']}.")
            return 0

    before = account_snapshot(client, plan)
    assert_protected_before(before, plan, allow_applied=False)
    keyword_ops, rsa_ops, pause_old_ops, campaign_op = build_operations(client, plan, before)
    validate_only(client, keyword_ops, rsa_ops, pause_old_ops, campaign_op)
    dry_run = {
        "mode": "validate_only",
        "validated_at": utc_now(),
        "plan_hash": plan_hash(),
        "customer_id": CUSTOMER_ID,
        "campaign_id": CAMPAIGN_ID,
        "mutations": {
            "keyword_count": len(keyword_ops),
            "rsa_count": len(rsa_ops),
            "poor_rsa_pause_count": len(pause_old_ops),
            "cpc_ceiling_from_micros": before["campaign"]["cpc_bid_ceiling_micros"],
            "cpc_ceiling_to_micros": int(plan["metadata"]["target_cpc_ceiling_micros"]),
            "daily_budget_change": False,
            "targeting_change": False,
            "network_change": False,
            "conversion_change": False,
            "negative_keyword_change": False,
            "app_campaign_change": False,
        },
        "before": before,
        "rollback": plan["metadata"]["rollback"],
    }
    write_json_atomic(DRY_RUN_PATH, dry_run)
    if not args.apply:
        print(DRY_RUN_PATH)
        print(f"Validate-only passed: {len(keyword_ops)} keywords, {len(rsa_ops)} paused-create RSAs, {len(pause_old_ops)} poor RSAs to displace, CPC ceiling INR 10 -> INR 18; budget fixed at INR 20/day.")
        return 0

    write_json_atomic(BEFORE_PATH, {**dry_run, "mode": "before_apply"})
    created_keywords: list[str] = []
    created_ads: list[str] = []
    paused_old_ads: list[str] = []
    try:
        response = client.get_service("AdGroupCriterionService").mutate_ad_group_criteria(
            customer_id=CUSTOMER_ID, operations=keyword_ops
        )
        created_keywords = [item.resource_name for item in response.results]
        response = client.get_service("AdGroupAdService").mutate_ad_group_ads(
            customer_id=CUSTOMER_ID, operations=rsa_ops
        )
        created_ads = [item.resource_name for item in response.results]
        response = client.get_service("AdGroupAdService").mutate_ad_group_ads(
            customer_id=CUSTOMER_ID, operations=pause_old_ops
        )
        paused_old_ads = [item.resource_name for item in response.results]
        set_ad_statuses(client, created_ads, "ENABLED")
        client.get_service("CampaignService").mutate_campaigns(
            customer_id=CUSTOMER_ID, operations=[campaign_op]
        )
        changes = {
            "created_keyword_resources": created_keywords,
            "created_ad_resources": created_ads,
            "paused_old_ad_resources": paused_old_ads,
            "cpc_ceiling_from_micros": before["campaign"]["cpc_bid_ceiling_micros"],
            "cpc_ceiling_to_micros": int(plan["metadata"]["target_cpc_ceiling_micros"]),
        }
        verification = verify_after(client, plan, before, changes)
        result = {
            "mode": "apply",
            "applied_at": utc_now(),
            "plan_hash": plan_hash(),
            "before": before,
            "changes": changes,
            "verification": verification,
        }
        write_json_atomic(LIVE_PATH, result)
    except Exception:
        pause_resources(client, created_keywords, created_ads)
        set_ad_statuses(client, paused_old_ads, "ENABLED")
        set_campaign_cpc(client, int(plan["metadata"]["current_cpc_ceiling_micros"]))
        raise

    print(LIVE_PATH)
    print(f"Applied and verified: {len(created_keywords)} keywords, {len(created_ads)} new RSAs, {len(paused_old_ads)} poor RSAs paused, CPC ceiling INR 18; Search budget remains INR 20/day.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
