"""SQLAlchemy ORM models for SYL."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    google_id = Column(String(255), nullable=True, unique=True)
    tier = Column(String(20), default="free")
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    syllabuses = relationship("Syllabus", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("StudySession", back_populates="user", cascade="all, delete-orphan")


class Syllabus(Base):
    __tablename__ = "syllabuses"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    course_code = Column(String(50), nullable=True)
    topic_tree = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="syllabuses")
    documents = relationship("Document", back_populates="syllabus", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="syllabus", cascade="all, delete-orphan")
    sessions = relationship("StudySession", back_populates="syllabus", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    syllabus_id = Column(UUID(as_uuid=False), ForeignKey("syllabuses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    filename = Column(String(255), nullable=False)
    page_count = Column(Integer, nullable=True)
    processing_status = Column(String(20), default="pending")
    processing_progress = Column(Integer, default=0)
    last_processed_chunk = Column(Integer, default=0)  # for resumable processing
    storage_path = Column(String(500), nullable=False)
    ocr_pages = Column(JSONB, default=list)  # list of page numbers that used OCR
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('TEXTBOOK', 'NOTES', 'SYLLABUS')", name="document_role_check"),
    )

    syllabus = relationship("Syllabus", back_populates="documents")
    problems = relationship("Problem", back_populates="document", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    syllabus_id = Column(UUID(as_uuid=False), ForeignKey("syllabuses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    prerequisites = Column(ARRAY(UUID(as_uuid=False)), default=list)
    estimated_depth = Column(String(20), nullable=True)
    graph_position_x = Column(Float, nullable=True)
    graph_position_y = Column(Float, nullable=True)
    display_order = Column(Integer, nullable=True)

    syllabus = relationship("Syllabus", back_populates="topics")
    progress = relationship("TopicProgress", back_populates="topic", cascade="all, delete-orphan")


class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    syllabus_id = Column(UUID(as_uuid=False), ForeignKey("syllabuses.id", ondelete="CASCADE"), nullable=False)
    current_topic_id = Column(UUID(as_uuid=False), ForeignKey("topics.id"), nullable=True)
    current_position_description = Column(Text, nullable=True)
    deviation_stack = Column(JSONB, default=list)
    session_summary = Column(Text, nullable=True)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="sessions")
    syllabus = relationship("Syllabus", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    session_id = Column(UUID(as_uuid=False), ForeignKey("study_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    citations = Column(JSONB, nullable=True)
    intent_classification = Column(String(20), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    llm_provider = Column(String(20), nullable=True)  # 'claude' | 'openai' | 'fallback'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="message_role_check"),
    )

    session = relationship("StudySession", back_populates="messages")


class TopicProgress(Base):
    __tablename__ = "topic_progress"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(UUID(as_uuid=False), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="not_started")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "topic_id", name="uq_user_topic_progress"),)

    topic = relationship("Topic", back_populates="progress")


class Problem(Base):
    __tablename__ = "problems"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    document_id = Column(UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    problem_number = Column(String(50), nullable=True)
    problem_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=False)
    chapter = Column(String(255), nullable=True)
    rank_tier = Column(String(20), nullable=True)
    similarity_score = Column(Float, nullable=True)
    qdrant_id = Column(String(255), nullable=True)

    document = relationship("Document", back_populates="problems")
    progress = relationship("ProblemProgress", back_populates="problem", cascade="all, delete-orphan")


class ProblemProgress(Base):
    __tablename__ = "problem_progress"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id = Column(UUID(as_uuid=False), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="todo")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("user_id", "problem_id", name="uq_user_problem_progress"),)

    problem = relationship("Problem", back_populates="progress")


class NoteTextbookMapping(Base):
    __tablename__ = "note_textbook_mappings"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    note_chunk_qdrant_id = Column(String(255), nullable=False)
    textbook_chunk_qdrant_id = Column(String(255), nullable=False)
    similarity_score = Column(Float, nullable=False)
    confidence = Column(String(10), nullable=True)
    syllabus_id = Column(UUID(as_uuid=False), ForeignKey("syllabuses.id", ondelete="CASCADE"), nullable=False)


class CitationFeedback(Base):
    __tablename__ = "citation_feedback"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    message_id = Column(UUID(as_uuid=False), ForeignKey("messages.id"), nullable=True)
    cited_page = Column(Integer, nullable=True)
    reported_incorrect = Column(Boolean, default=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
