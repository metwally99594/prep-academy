"""
Community Index Audit — detect hot query paths, recommend indexes,
estimate collection scan risks, identify missing compound indexes.

This is a read-only analysis helper. It does NOT create or drop indexes.
Run manually via: python -m services.community_index_audit
"""
from typing import Any


def analyze_query_patterns() -> dict[str, Any]:
    """Return all known community query patterns with index coverage assessment."""
    patterns = [
        # ── community_posts ──
        {
            "collection": "community_posts",
            "pattern": 'find({"status":"published"}).sort("created_at",-1).limit(20)',
            "used_in": "find_duplicate_post, feed offset pagination",
            "existing_index": 'status:1, created_at:-1',
            "covered": True,
            "recommendation": None,
        },
        {
            "collection": "community_posts",
            "pattern": 'find({"status":"published", sort_field:{$lt:val}}).sort(sort_spec).limit(N)',
            "used_in": "paginate_feed cursor mode",
            "existing_index": 'status:1, created_at:-1',
            "covered": True,
            "recommendation": 'Add (status:1, created_at:-1, _id:1) for cursor tiebreaker stability',
        },
        {
            "collection": "community_posts",
            "pattern": 'find({"author_id":X}).sort("created_at",-1).skip().limit()',
            "used_in": "get_my_posts",
            "existing_index": 'author_id:1, created_at:-1',
            "covered": True,
            "recommendation": None,
        },
        {
            "collection": "community_posts",
            "pattern": 'aggregate([$match:{status:"published",created_at:{$gte:since}},$sort:{hot_score:-1},$limit:N])',
            "used_in": "get_trending",
            "existing_index": 'status:1, created_at:-1',
            "covered": True,
            "recommendation": None,
        },
        # ── community_comments ──
        {
            "collection": "community_comments",
            "pattern": 'find({"post_id":X}).sort("created_at",1).to_list(N)',
            "used_in": "get_post",
            "existing_index": 'post_id:1, created_at:1',
            "covered": True,
            "recommendation": None,
        },
        # ── notifications ──
        {
            "collection": "notifications",
            "pattern": 'find({"user_id":X}).sort("created_at",-1).to_list(N+1)',
            "used_in": "get_user_notifications",
            "existing_index": "NONE",
            "covered": False,
            "recommendation": 'CREATE: db.notifications.createIndex({user_id:1, created_at:-1})',
        },
        {
            "collection": "notifications",
            "pattern": 'count_documents({"user_id":X, "read":false})',
            "used_in": "get_user_notifications (unread_count)",
            "existing_index": "NONE",
            "covered": False,
            "recommendation": 'CREATE: db.notifications.createIndex({user_id:1, read:1, created_at:-1})',
        },
        {
            "collection": "notifications",
            "pattern": 'update_many({"user_id":X, "read":false}, {$set:{read:true}})',
            "used_in": "mark_all_read",
            "existing_index": "NONE",
            "covered": False,
            "recommendation": 'CREATE: db.notifications.createIndex({user_id:1, read:1})',
        },
        {
            "collection": "notifications",
            "pattern": 'find_one({"user_id":X, type:Y, "data.aggregate_key":Z, read:false})',
            "used_in": "aggregate_notification",
            "existing_index": "NONE",
            "covered": False,
            "recommendation": 'CREATE: db.notifications.createIndex({user_id:1, type:1, "data.aggregate_key":1, read:1})',
        },
        # ── community_reactions ──
        {
            "collection": "community_reactions",
            "pattern": 'find_one({"user_id":X, "target_type":Y, "target_id":Z})',
            "used_in": "handle_reaction_toggle",
            "existing_index": 'user_id:1, target_type:1, target_id:1 (unique)',
            "covered": True,
            "recommendation": None,
        },
        # ── community_moderation_queue ──
        {
            "collection": "community_moderation_queue",
            "pattern": 'find({reviewed:X, severity:Y}).sort("created_at",-1)',
            "used_in": "get_moderation_queue, paginate_moderation_queue",
            "existing_index": 'reviewed:1, severity:-1, created_at:-1',
            "covered": True,
            "recommendation": None,
        },
        {
            "collection": "community_moderation_queue",
            "pattern": 'insert_one with unique constraint on (target_type, target_id)',
            "used_in": "handle_moderation_queue_insert",
            "existing_index": 'target_type:1, target_id:1 (unique)',
            "covered": True,
            "recommendation": None,
        },
        # ── community_moderation_audit ──
        {
            "collection": "community_moderation_audit",
            "pattern": 'insert_one + potential find().sort("created_at",-1)',
            "used_in": "take_moderation_action (audit trail)",
            "existing_index": "NONE (not created in server.py)",
            "covered": False,
            "recommendation": 'CREATE: db.community_moderation_audit.createIndex({created_at:-1})',
        },
        # ── users ──
        {
            "collection": "users",
            "pattern": 'find_one({"name":X})',
            "used_in": "notify_mentioned_users",
            "existing_index": "NONE on 'name' field",
            "covered": False,
            "recommendation": 'CREATE: db.users.createIndex({name:1})  (if @mention is heavily used)',
        },
    ]
    return {"patterns": patterns, "total": len(patterns)}


def estimate_collection_scan_risk() -> list[dict[str, Any]]:
    """Identify query paths with no or insufficient index coverage."""
    uncovered = []
    for p in analyze_query_patterns()["patterns"]:
        if not p["covered"]:
            uncovered.append({
                "collection": p["collection"],
                "pattern": p["pattern"],
                "used_in": p["used_in"],
                "risk": "COLLECTION_SCAN",
                "recommendation": p["recommendation"],
            })
    return uncovered


def recommend_missing_indexes() -> list[dict[str, str]]:
    """Return recommended indexes with rationale, in priority order."""
    return [
        {
            "priority": "HIGH",
            "collection": "notifications",
            "index": "{user_id:1, created_at:-1}",
            "rationale": "Primary query path for get_user_notifications cursor pagination. Without this, every notification fetch scans the full collection.",
        },
        {
            "priority": "HIGH",
            "collection": "notifications",
            "index": "{user_id:1, read:1, created_at:-1}",
            "rationale": "Covers unread_count query and mark_all_read filter. Compound index enables covered query for count_documents.",
        },
        {
            "priority": "MEDIUM",
            "collection": "notifications",
            "index": '{user_id:1, type:1, "data.aggregate_key":1, read:1}',
            "rationale": "Covers aggregate_notification find-one for merging. The read:false filter makes this a targeted lookup.",
        },
        {
            "priority": "MEDIUM",
            "collection": "community_moderation_audit",
            "index": "{created_at:-1}",
            "rationale": "Admin audit log listing. No index exists on this collection; every admin audit view scans the full collection.",
        },
        {
            "priority": "LOW",
            "collection": "community_posts",
            "index": "{status:1, created_at:-1, _id:1}",
            "rationale": "Cursor pagination tiebreaker. Prevents duplicate/skipped results on page boundaries during high write volume.",
        },
        {
            "priority": "LOW",
            "collection": "users",
            "index": "{name:1}",
            "rationale": "Covers notify_mentioned_users find-one by username. Only needed if @mention feature is heavily used.",
        },
    ]


def print_audit_report():
    """Print a human-readable index audit report."""
    import json
    print("=" * 72)
    print("  COMMUNITY INDEX AUDIT REPORT")
    print("=" * 72)

    print("\n## Missing Indexes (Collection Scan Risk)\n")
    for item in estimate_collection_scan_risk():
        print(f"  [{item['risk']}] {item['collection']}")
        print(f"         Pattern: {item['pattern']}")
        print(f"         Used in: {item['used_in']}")
        print(f"         Fix:     {item['recommendation']}")
        print()

    print("\n## Recommended Indexes (Priority Order)\n")
    for idx, r in enumerate(recommend_missing_indexes(), 1):
        print(f"  {idx}. [{r['priority']}] {r['collection']}")
        print(f"      Index: {r['index']}")
        print(f"      Why:   {r['rationale']}")
        print()

    print("\n## Coverage Summary\n")
    patterns = analyze_query_patterns()["patterns"]
    covered = sum(1 for p in patterns if p["covered"])
    total = len(patterns)
    print(f"  Query patterns analyzed: {total}")
    print(f"  Covered by indexes:      {covered}")
    print(f"  Collection scans:        {total - covered}")
    print(f"  Coverage rate:           {covered}/{total} ({100 * covered // total}%)")
    print("=" * 72)


if __name__ == "__main__":
    print_audit_report()
