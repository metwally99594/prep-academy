from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid


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
    tags: Optional[List[str]] = []
    drag_drop_items: Optional[List[DragDropItem]] = None
    drag_drop_categories: Optional[List[DragDropCategory]] = None
    blank_text: Optional[str] = None
    blank_answers: Optional[List[str]] = None

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
    tags: Optional[List[str]] = None
    drag_drop_items: Optional[List[DragDropItem]] = None
    drag_drop_categories: Optional[List[DragDropCategory]] = None
    blank_text: Optional[str] = None
    blank_answers: Optional[List[str]] = None

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
    created_at: Optional[str] = None
    tags: Optional[List[str]] = []
    drag_drop_items: Optional[List[dict]] = None
    drag_drop_categories: Optional[List[dict]] = None
    blank_text: Optional[str] = None
    blank_answers: Optional[List[str]] = None

class AnswerSubmit(BaseModel):
    question_id: str
    selected_choice_ids: Optional[List[str]] = []
    drag_drop_answer: Optional[Dict[str, str]] = None
    blank_answer: Optional[str] = None

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
    model: Optional[str] = "gpt-4o"
    language: Optional[str] = "de"

class AIChatRequest(BaseModel):
    question_id: str
    user_message: str
    context: Optional[str] = None
    model: Optional[str] = "gpt-4o"
    language: Optional[str] = "de"

class CustomQuizRequest(BaseModel):
    specialties: List[str] = []
    text_search: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    exam_location: Optional[str] = None
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
    content: str = Field(..., min_length=1, max_length=5000)
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
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=10000)
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
    content: str = Field(..., min_length=1, max_length=5000)


class CommunityCommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


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
