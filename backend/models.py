from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    is_admin: bool = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    is_admin: bool
    created_at: str
    picture: Optional[str] = None
    auth_provider: Optional[str] = None

class GoogleAuthCallback(BaseModel):
    session_id: str

class QuestionChoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    text_de: Optional[str] = None
    is_correct: bool = False

class DragDropItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    correct_category: str

class DragDropCategory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str

class QuestionCreate(BaseModel):
    specialty_id: str
    year: int
    question_text: str
    question_text_de: Optional[str] = None
    question_type: Optional[str] = "single_choice"
    choices: Optional[List[QuestionChoice]] = []
    explanation: Optional[str] = None
    explanation_de: Optional[str] = None
    image_base64: Optional[str] = None
    exam_location: Optional[str] = "vienna"
    country: Optional[str] = None
    status: Optional[str] = "published"
    tags: Optional[List[str]] = []
    drag_drop_items: Optional[List[DragDropItem]] = None
    drag_drop_categories: Optional[List[DragDropCategory]] = None
    blank_text: Optional[str] = None
    blank_answers: Optional[List[str]] = None
    blanks: Optional[List[dict]] = None

class QuestionUpdate(BaseModel):
    specialty_id: Optional[str] = None
    year: Optional[int] = None
    question_text: Optional[str] = None
    question_text_de: Optional[str] = None
    question_type: Optional[str] = None
    choices: Optional[List[QuestionChoice]] = None
    explanation: Optional[str] = None
    explanation_de: Optional[str] = None
    image_base64: Optional[str] = None
    exam_location: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    drag_drop_items: Optional[List[DragDropItem]] = None
    drag_drop_categories: Optional[List[DragDropCategory]] = None
    blank_text: Optional[str] = None
    blank_answers: Optional[List[str]] = None
    blanks: Optional[List[dict]] = None

class QuestionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    specialty_id: str
    year: int = 2024
    question_text: Optional[str] = ""
    question_text_de: Optional[str] = None
    question_type: Optional[str] = "single_choice"
    choices: Optional[List[dict]] = []
    choices_de: Optional[List[dict]] = None
    correct_answers: Optional[List[str]] = None
    explanation: Optional[str] = None
    explanation_de: Optional[str] = None
    image_base64: Optional[str] = None
    exam_location: Optional[str] = "vienna"
    country: Optional[str] = None
    status: Optional[str] = "published"
    created_at: Optional[str] = None
    tags: Optional[List[str]] = []
    drag_drop_items: Optional[List[dict]] = None
    drag_drop_categories: Optional[list] = None
    blank_text: Optional[str] = None
    blank_answers: Optional[List[str]] = None
    blanks: Optional[List[dict]] = None
    generated_by_ai: Optional[bool] = None
    ai_model_used: Optional[str] = None
    source_notebook_id: Optional[str] = None

class AnswerSubmit(BaseModel):
    question_id: str
    selected_choice_ids: Optional[List[str]] = []
    drag_drop_answer: Optional[Dict[str, str]] = None
    blank_answer: Optional[str] = None
    blank_answers: Optional[List[str]] = None

class AnswerResult(BaseModel):
    is_correct: bool
    correct_choice_ids: List[str] = []
    explanation: Optional[str] = None
    xp_earned: Optional[int] = None
    total_xp: Optional[int] = None
    level: Optional[dict] = None
    leveled_up: Optional[bool] = None

class FavoriteCreate(BaseModel):
    question_id: str

class StatsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    total_questions: int
    correct_answers: int
    wrong_answers: int
    accuracy_percentage: float
    by_specialty: dict
    by_year: dict

class AIExplainRequest(BaseModel):
    question_id: str
    user_question: Optional[str] = None
    model: Optional[str] = "deepseek-chat"
    language: Optional[str] = "de"

class AIChatRequest(BaseModel):
    question_id: str
    user_message: str
    context: Optional[str] = None
    model: Optional[str] = "deepseek-chat"
    language: Optional[str] = "de"

class AITutorRequest(BaseModel):
    user_message: str
    model: Optional[str] = "deepseek-chat"
    language: Optional[str] = "de"
    conversation_id: Optional[str] = None
    specialty_id: Optional[str] = None
    chapter_index: Optional[int] = None
    mcq_options: Optional[str] = None  # "A: text\nB: text\nC: text\nD: text" for MCQ analysis

class MCQChoice(BaseModel):
    option: str
    reason: str

class MCQAnalysis(BaseModel):
    correct_answer: str
    correct_reason: str
    wrong_answers: List[MCQChoice]

class MetsuRequest(BaseModel):
    question: str
    specialty_id: Optional[str] = None
    chapter_index: Optional[int] = None
    force_full: bool = False  # True = Tier 2 (6 models), False = Tier 1 (3 models)

class CustomQuizRequest(BaseModel):
    specialties: List[str] = []
    text_search: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    exam_location: Optional[str] = None
    country: Optional[str] = None
    favorites_only: bool = False
    tags: Optional[List[str]] = None
    limit: int = 50
    mode: str = "exam"
    question_types: Optional[List[str]] = None

class SpecialtyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    name_de: str
    icon: str
    question_count: int

class NotebookChatRequest(BaseModel):
    notebook_id: str
    message: str
    chunk_index: Optional[int] = None

class AnalyzeRequest(BaseModel):
    image_base64: str = ""
    images: Optional[List[str]] = None
    report_type: str = "ECG"
    clinical_context: str = ""

class BulkCityUpdate(BaseModel):
    question_ids: List[str]
    exam_location: str

class BulkDeleteRequest(BaseModel):
    question_ids: List[str]


# ═══════════════════════════════════════════════════════════════
# MESSAGING — User ↔ Admin Conversation System
# ═══════════════════════════════════════════════════════════════

class MessageAttachment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    mime_type: str
    size_bytes: int = 0
    image_base64: Optional[str] = None
    type: str = "other"


class MessageSend(BaseModel):
    conversation_id: Optional[str] = None
    recipient_id: str
    subject: Optional[str] = None
    content: str = Field(default="", max_length=5000)
    attachments: List[MessageAttachment] = []


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    conversation_id: str
    sender_id: str
    sender_role: str
    content: str
    attachments: list = []
    read_by: list = []
    is_system_message: bool = False
    created_at: str


class ConversationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    participants: list = []
    subject: Optional[str] = None
    last_message_at: Optional[str] = None
    last_message_preview: Optional[str] = None
    last_message_sender_id: Optional[str] = None
    unread_count: int = 0
    status: str = "active"
    escalation_level: int = 0
    tags: list = []
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse] = []
    total: int = 0


class EscalationUpdate(BaseModel):
    escalation_level: int = Field(default=0, ge=0, le=3)
    reason: Optional[str] = None


class ConversationTagsUpdate(BaseModel):
    tags: List[str] = []


# ═══════════════════════════════════════════════════════════════
# MEDICAL COMMUNITY — Posts, Comments, Moderation
# ═══════════════════════════════════════════════════════════════

class CommunityPostCreate(BaseModel):
    title: str
    content: str
    specialty_tags: List[str] = []
    topic_tags: List[str] = []
    type: str = "discussion"
    image_ids: List[str] = []
    media: List[dict] = []


class CommunityPostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    specialty_tags: Optional[List[str]] = None
    topic_tags: Optional[List[str]] = None


class CommunityPostResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    author_id: str
    author_name: Optional[str] = None
    title: str
    content: str
    content_html: Optional[str] = None
    specialty_tags: list = []
    topic_tags: list = []
    type: str = "discussion"
    status: str = "published"
    stats: dict = {}
    image_ids: list = []
    media: list = []
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    ai_summary: Optional[str] = None
    educational_safety_approved: bool = False
    created_at: str
    updated_at: str


class CommunityPostListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    posts: List[CommunityPostResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    next_cursor: Optional[str] = None


class CommunityCommentCreate(BaseModel):
    post_id: str
    parent_id: Optional[str] = None
    content: str


class CommunityCommentUpdate(BaseModel):
    content: str


class CommunityCommentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    post_id: str
    parent_id: Optional[str] = None
    author_id: str
    author_name: Optional[str] = None
    content: str
    status: str = "published"
    stats: dict = {}
    created_at: str
    updated_at: str


class CommunityReaction(BaseModel):
    target_type: str
    target_id: str
    reaction: str = "upvote"


class CommunityReport(BaseModel):
    target_type: str
    target_id: str
    reason: str
    description: Optional[str] = None


class CommunityFeedParams(BaseModel):
    specialty: Optional[str] = None
    topic: Optional[str] = None
    type: Optional[str] = None
    sort: str = "recent"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None


class ModerationAction(BaseModel):
    target_type: str
    target_id: str
    action: str
    reason: Optional[str] = None


class AccessRequestCreate(BaseModel):
    feature_pack: str = "advanced_features"


class AccessRequestUpdate(BaseModel):
    status: str  # "approved" | "rejected"


class ContactRequestCreate(BaseModel):
    """Public contact / interest form submitted by non-authenticated visitors."""
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=40)
    message: Optional[str] = Field(None, max_length=1000)
    feature_pack: Optional[str] = "advanced_features"


# ── Question Management System (QMS) Models ──

class QuestionImportItem(BaseModel):
    specialty_id: str
    question_text_de: str
    question_type: str = "mcq"
    choices_de: Optional[List] = None
    explanation_de: Optional[str] = None
    year: Optional[int] = None
    exam_location: Optional[str] = None
    country: Optional[str] = None
    tags: Optional[List[str]] = []
    drag_drop_items: Optional[List[dict]] = None
    drag_drop_categories: Optional[List] = None
    blanks: Optional[List[dict]] = None

class QuestionImportRequest(BaseModel):
    questions: List[QuestionImportItem]
    filename: Optional[str] = "paste"

class ValidationError(BaseModel):
    index: int
    field: str
    message: str

class QuestionImportLog(BaseModel):
    id: str
    admin_email: str
    filename: str
    imported_count: int
    skipped_duplicates: int
    validation_errors: int
    errors: List[ValidationError]
    created_at: float
    duration_ms: int


# ═══════════════════════════════════════════════════════════════
# QUESTION IMPORT & OPTION COMPLETION TOOL
# ═══════════════════════════════════════════════════════════════

class ParsedQuestion(BaseModel):
    """A single question extracted from an uploaded file."""
    question: str
    options: List[str] = []
    correct_answers: List[str] = []
    generated_options: List[str] = []
    source_file: str = ""
    status: str = "parsed"  # parsed | completed | failed
    error: Optional[str] = None


class ImportFileInfo(BaseModel):
    """Metadata about an uploaded file within an import job."""
    filename: str
    file_type: str = ""  # pdf | markdown
    status: str = "uploaded"  # uploaded | processing | parsed | failed
    error: Optional[str] = None
    questions_count: int = 0


class ImportJob(BaseModel):
    """Tracks a complete import workflow from upload to export."""
    id: str = Field(default_factory=lambda: f"imp_{uuid.uuid4().hex[:12]}")
    status: str = "uploaded"  # uploaded | processing | parsed | validating | completed | failed
    files: List[ImportFileInfo] = []
    questions: List[ParsedQuestion] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ImportResponse(BaseModel):
    import_id: str
    status: str


class ValidationResult(BaseModel):
    question_index: int
    valid: bool
    errors: List[str] = []


class ValidationSummary(BaseModel):
    total_questions: int
    valid: int
    invalid: int
    errors: List[dict] = []


class GenerateOptionsResponse(BaseModel):
    import_id: str
    processed: int
    updated: int
    skipped: int
    failed: int
    total: int
    results: List[dict] = []


class ExportQuestion(BaseModel):
    index: int
    question: str
    original_options: List[str]
    generated_options: List[str]
    final_options: List[str]
    correct_answers: List[str]
