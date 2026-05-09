"""
Moderation Pipeline — auto-moderation rules, medical content review, queue management.

Pure functions + rule-based decisions. AI moderation interface prepared for future.
"""
import time
from typing import Optional


# ── Auto-moderation rules ──

AUTO_QUEUE_REASONS = {
    "contains_html": "Contains raw HTML markup",
    "phi_detected": "Possible patient health information detected",
    "dangerous_advice": "Potentially dangerous medical advice",
    "multiple_reports": "Reported by multiple users",
    "high_report_rate": "Reported multiple times in short period",
    "new_user_links": "New user posting external links",
    "all_caps_title": "Title is all caps",
}


def evaluate_auto_moderation(
    is_new_user: bool = False,
    contains_html: bool = False,
    phi_findings: Optional[list[str]] = None,
    dangerous_advice: Optional[list[str]] = None,
    report_count: int = 0,
    recent_reports: int = 0,
    has_external_links: bool = False,
    title_is_all_caps: bool = False,
) -> tuple[bool, str, str]:
    """
    Evaluate rules and decide: pass, queue, or hide.

    Returns: (should_queue: bool, reason_key: str, severity: str)
    severity: "low" | "medium" | "high" | "critical"
    """
    if phi_findings and len(phi_findings) > 0:
        return True, "phi_detected", "high"
    if dangerous_advice and len(dangerous_advice) > 0:
        return True, "dangerous_advice", "critical"
    if contains_html:
        return True, "contains_html", "medium"
    if recent_reports >= 3:
        return True, "high_report_rate", "medium"
    if report_count >= 3:
        return True, "multiple_reports", "medium"
    if is_new_user and has_external_links:
        return True, "new_user_links", "low"
    if title_is_all_caps:
        return True, "all_caps_title", "low"
    return False, "", ""


def is_title_all_caps(title: str) -> bool:
    if not title or len(title) < 3:
        return False
    letters = [c for c in title if c.isalpha()]
    if len(letters) < 3:
        return False
    return sum(1 for c in letters if c.isupper()) / len(letters) > 0.8


def has_external_links(text: str) -> bool:
    import re
    return bool(re.search(r"https?://(?:[^\s])+", text))


# ── Moderation queue entry builder ──

def build_moderation_entry(
    target_type: str,
    target_id: str,
    reason: str,
    reason_key: str,
    severity: str,
    ai_result: Optional[dict] = None,
) -> dict:
    return {
        "id": __import__("uuid").uuid4().hex,
        "target_type": target_type,
        "target_id": target_id,
        "reason": reason,
        "reason_key": reason_key,
        "ai_result": ai_result,
        "severity": severity,
        "reviewed": False,
        "reviewed_by": None,
        "reviewed_at": None,
        "action_taken": None,
        "created_at": time.time(),
    }


# ── AI Moderation interface (prepared for future) ──

AI_MODERATION_CATEGORIES = {
    "spam": "Commercial spam or promotional content",
    "misinformation": "Medical misinformation or unsubstantiated claims",
    "inappropriate": "Inappropriate, offensive, or harmful content",
    "phi": "Patient health information or personal data",
    "dangerous_advice": "Dangerous medical advice that could cause harm",
    "low_quality": "Low quality content (too short, gibberish)",
}


class AIModerationResult:
    """Placeholder for future AI-powered moderation."""

    def __init__(self) -> None:
        self.flagged: bool = False
        self.categories: list[str] = []
        self.scores: dict[str, float] = {}
        self.reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "flagged": self.flagged,
            "categories": self.categories,
            "scores": self.scores,
            "reason": self.reason,
        }


# ── Report threshold helpers ──

REPORT_HIDE_THRESHOLD = 5
REPORT_QUEUE_THRESHOLD = 3
REPORT_RATE_WINDOW = 3600  # 1 hour
REPORT_RATE_THRESHOLD = 3  # 3 reports in 1 hour


def should_auto_hide(report_count: int) -> bool:
    return report_count >= REPORT_HIDE_THRESHOLD


def should_auto_queue(report_count: int) -> bool:
    return report_count >= REPORT_QUEUE_THRESHOLD


# ── Content quality check ──

MIN_POST_LENGTH = 50
MIN_COMMENT_LENGTH = 10


def check_content_quality(text: str, min_length: int = MIN_POST_LENGTH) -> Optional[str]:
    stripped = text.strip()
    if len(stripped) < min_length:
        return f"Content too short ({len(stripped)} chars, minimum {min_length})"
    word_count = len(stripped.split())
    if word_count < 5:
        return "Content too short (minimum 5 words)"
    return None
