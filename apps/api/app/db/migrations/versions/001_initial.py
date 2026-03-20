"""Initial database schema.

Revision ID: 001
Revises: 
Create Date: 2026-03-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Syllabuses table
    op.create_table(
        'syllabuses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('course_name', sa.String(255), nullable=False),
        sa.Column('topic_count', sa.Integer(), default=0, nullable=False),
        sa.Column('graph_data', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('syllabus_id', sa.String(36), sa.ForeignKey('syllabuses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),  # TEXTBOOK, NOTES, SYLLABUS
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('total_pages', sa.Integer(), nullable=True),
        sa.Column('processed_pages', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Note Textbook Mappings Table
    op.create_table(
        'note_textbook_mappings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('syllabus_id', sa.String(36), sa.ForeignKey('syllabuses.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('note_doc_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('note_page', sa.Integer(), nullable=False),
        sa.Column('textbook_doc_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('textbook_page', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.String(20), nullable=False), # HIGH, MEDIUM, LOW
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Sessions table (accessed primarily by Go Orchestrator)
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('syllabus_id', sa.String(36), sa.ForeignKey('syllabuses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic_id', sa.String(255), nullable=True),
        sa.Column('topic_name', sa.String(255), nullable=True),
        sa.Column('deviation_stack', JSONB(), nullable=True),  # Pushed deviation topics
        sa.Column('message_count', sa.Integer(), default=0, nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Problems table
    op.create_table(
        'problems',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('syllabus_id', sa.String(36), sa.ForeignKey('syllabuses.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('problem_number', sa.String(50), nullable=True),
        sa.Column('problem_text', sa.Text(), nullable=False),
        sa.Column('chapter', sa.String(255), nullable=True),
        sa.Column('rank_tier', sa.String(20), nullable=True), # EXAM_LIKELY, GOOD_PRACTICE, OPTIONAL
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Problem Progress table
    op.create_table(
        'problem_progress',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('problem_id', sa.String(36), sa.ForeignKey('problems.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='todo'), # todo, in_progress, done
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    sa.UniqueConstraint('problem_id', 'user_id', name='uq_problem_user')


def downgrade() -> None:
    op.drop_table('problem_progress')
    op.drop_table('problems')
    op.drop_table('sessions')
    op.drop_table('note_textbook_mappings')
    op.drop_table('documents')
    op.drop_table('syllabuses')
    op.drop_table('users')
