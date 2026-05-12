"""
Moderation Pipeline — auto-moderation rules, medical content review, queue management.

Pure functions + rule-based decisions. AI moderation interface prepared for future.
"""
import re
import time
from typing import Optional


# ── Profanity filter (DE / EN / AR) ──

_DE_PROFANITY = re.compile(
    r"\b(?:arsch(?:loch)?|fick(?:en|st|t|e)?|scheiß(?:e|t|en)?|"
    r"mist(?:er)?|verdammt|wichser|hure|bastard|"
    r"schlampe|trottel|idiot|mongo|behinderte)\b",
    re.IGNORECASE,
)

_EN_PROFANITY = re.compile(
    r"\b(?:fuck(?:ing|er|ed|s)?|shit|bitch(?:es)?|ass(?:hole)?|"
    r"damn|cocksucker|dickhead|bastard|motherfucker)\b",
    re.IGNORECASE,
)

_AR_PROFANITY = re.compile(
    r"(?:كسم|شرموط|قحبة|ابن(?: ال)?كلب|خرة|كس|زبر|عير|نيّك|متناك|"
    r"منيوك|خنيث|لوطي|عرص|قواد|خول)",
)


def check_profanity(text: str) -> list[str]:
    """Check text for profanity in DE, EN, AR. Returns list of matched terms."""
    findings: list[str] = []
    for m in _DE_PROFANITY.finditer(text):
        findings.append(f"Profanity (DE): '{m.group()}'")
    for m in _EN_PROFANITY.finditer(text):
        findings.append(f"Profanity (EN): '{m.group()}'")
    for m in _AR_PROFANITY.finditer(text):
        findings.append(f"Profanity (AR): '{m.group()}'")
    return findings


# ── Spam & Suspicious Content Heuristics ──

_EMOJI_RE = re.compile(
    r"[\U0001F600-\U0001F64F"      # Emoticons
    r"\U0001F300-\U0001F5FF"        # Misc symbols
    r"\U0001F680-\U0001F6FF"        # Transport
    r"\U0001F1E0-\U0001F1FF"        # Flags
    r"\U00002702-\U000027B0"        # Dingbats
    r"\U000024C2-\U0001F251"        # Enclosed
    r"\u2600-\u27BF"                # Misc symbols
    r"\uFE00-\uFE0F"               # Variation selectors
    r"]+"
)

EMOJI_SPAM_THRESHOLD = 10
EMOJI_RATIO_THRESHOLD = 0.5

_link_store: dict[str, list[str]] = {}  # user_id -> list of URLs
LINK_SPAM_WINDOW = 300  # 5 minutes
LINK_SPAM_THRESHOLD = 3  # 3 identical links within window


def check_emoji_spam(text: str) -> list[str]:
    """Check text for emoji spam. Returns findings if threshold exceeded."""
    if not text:
        return []
    emojis = _EMOJI_RE.findall(text)
    if not emojis:
        return []
    total_emoji_chars = sum(len(e) for e in emojis)
    if total_emoji_chars >= EMOJI_SPAM_THRESHOLD:
        ratio = total_emoji_chars / max(len(text), 1)
        if ratio >= EMOJI_RATIO_THRESHOLD:
            return [f"Emoji spam: {total_emoji_chars} emoji chars ({ratio:.0%} of text)"]
    return []


def check_repeated_links(text: str) -> list[str]:
    """Check text for external links. Returns findings (per-call count check)."""
    urls = re.findall(r"https?://(?:[^\s])+", text)
    if len(urls) >= 3:
        return [f"Multiple external links: {len(urls)} URLs found"]
    return []


def track_user_link(user_id: str, url: str) -> bool:
    """Track a URL per user. Returns True if threshold exceeded (repeated link spam)."""
    now = time.time()
    cutoff = now - LINK_SPAM_WINDOW
    user_links = _link_store.get(user_id, [])
    user_links = [u for u in user_links if u[1] > cutoff]
    user_links.append((url, now))
    _link_store[user_id] = user_links
    count = sum(1 for u, _ in user_links if u == url)
    return count >= LINK_SPAM_THRESHOLD


def check_suspicious_account(user_age_days: float, recent_bursts: int) -> Optional[str]:
    """Heuristic: low account age + burst activity = suspicious."""
    if user_age_days < 7 and recent_bursts >= 3:
        return "Suspicious account: low age + burst activity"
    if user_age_days < 1 and recent_bursts >= 1:
        return "Suspicious account: first-day burst activity"
    return None


SHADOW_HIDE_THRESHOLD = 3
"""Number of auto-moderation events before content is silently shadow-hidden."""


MODERATOR_REASON_TEMPLATES = {
    "spam": "Commercial spam or promotional content — not allowed in medical community",
    "misinformation": "Medical misinformation or unsubstantiated claims — please provide sources",
    "inappropriate": "Inappropriate, offensive, or harmful content — violates community guidelines",
    "phi": "Patient health information detected — do not share personal medical data",
    "dangerous_advice": "Potentially dangerous medical advice that could cause harm",
    "low_quality": "Low quality content — please provide more detailed, substantive posts",
    "duplicate": "Duplicate content — already posted by you or another user",
    "off_topic": "Content not relevant to this community's medical focus",
    "profanity": "Profanity or offensive language — keep discussions professional",
    "link_spam": "Repeated external link posting — promotional content not allowed",
    "emoji_spam": "Excessive emoji use — please use text for substantive contributions",
}


# ── Auto-moderation rules ──

AUTO_QUEUE_REASONS = {
    "contains_html": "Contains raw HTML markup",
    "phi_detected": "Possible patient health information detected",
    "dangerous_advice": "Potentially dangerous medical advice",
    "multiple_reports": "Reported by multiple users",
    "high_report_rate": "Reported multiple times in short period",
    "new_user_links": "New user posting external links",
    "all_caps_title": "Title is all caps",
    "profanity": "Contains profanity or offensive language",
    "emoji_spam": "Excessive emoji use",
    "link_spam": "Repeated external link posting",
    "suspicious_account": "Suspicious account activity detected",
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
    profanity_findings: Optional[list[str]] = None,
    emoji_findings: Optional[list[str]] = None,
    link_findings: Optional[list[str]] = None,
    suspicious_account_reason: Optional[str] = None,
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
    if profanity_findings and len(profanity_findings) > 0:
        return True, "profanity", "medium"
    if suspicious_account_reason:
        return True, "suspicious_account", "medium"
    if contains_html:
        return True, "contains_html", "medium"
    if recent_reports >= 3:
        return True, "high_report_rate", "medium"
    if report_count >= 3:
        return True, "multiple_reports", "medium"
    if emoji_findings and len(emoji_findings) > 0:
        return True, "emoji_spam", "low"
    if link_findings and len(link_findings) > 0:
        return True, "link_spam", "low"
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


# ── Auto-lock (in-memory offense tracking) ──

_user_offense_store: dict[str, list[float]] = {}
AUTO_LOCK_THRESHOLD = 3
AUTO_LOCK_WINDOW = 86400 * 7  # 7 days


def increment_offense(author_id: str) -> bool:
    """Increment offense count for a user. Returns True if threshold reached (should auto-lock)."""
    now = time.time()
    cutoff = now - AUTO_LOCK_WINDOW
    offenses = _user_offense_store.get(author_id, [])
    offenses = [t for t in offenses if t > cutoff]
    offenses.append(now)
    _user_offense_store[author_id] = offenses
    return len(offenses) >= AUTO_LOCK_THRESHOLD


def get_recent_offenses(author_id: str) -> int:
    """Return the number of recent offenses for a user within the lock window."""
    cutoff = time.time() - AUTO_LOCK_WINDOW
    offenses = _user_offense_store.get(author_id, [])
    return len([t for t in offenses if t > cutoff])


# ── Audit log entry builder ──


def build_audit_entry(
    action: str,
    target_type: str,
    target_id: str,
    admin_id: str,
    reason: Optional[str] = None,
    details: Optional[dict] = None,
) -> dict:
    return {
        "id": __import__("uuid").uuid4().hex,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "admin_id": admin_id,
        "reason": reason,
        "details": details or {},
        "created_at": time.time(),
    }


# ── Content quality check (disabled — no character limits) ──


def check_content_quality(text: str, min_length: int = 0) -> Optional[str]:
    return None
