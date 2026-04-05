package db

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"time"

	_ "github.com/lib/pq"
	"github.com/syl/orchestrator/internal/session"
)

// PostgresStore implements a PostgreSQL-backed session store.
type PostgresStore struct {
	db *sql.DB
}

// NewPostgresStore creates a new PostgreSQL store.
func NewPostgresStore() (*PostgresStore, error) {
	connStr := os.Getenv("DATABASE_URL")
	if connStr == "" {
		return nil, fmt.Errorf("DATABASE_URL not set")
	}

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, fmt.Errorf("db open: %w", err)
	}

	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("db ping: %w", err)
	}

	return &PostgresStore{db: db}, nil
}

// Save inserts or updates a session state.
func (s *PostgresStore) Save(ctx context.Context, sess *session.SessionState) error {
	query := `
		INSERT INTO sessions (id, user_id, syllabus_id, topic_id, topic_name, deviation_stack, message_count, summary, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		ON CONFLICT (id) DO UPDATE SET
			topic_id = EXCLUDED.topic_id,
			topic_name = EXCLUDED.topic_name,
			deviation_stack = EXCLUDED.deviation_stack,
			message_count = EXCLUDED.message_count,
			summary = EXCLUDED.summary,
			updated_at = EXCLUDED.updated_at
	`
	_, err := s.db.ExecContext(ctx, query,
		sess.ID, sess.UserID, sess.SyllabusID, sess.TopicID, sess.TopicName,
		sess.DeviationStack, sess.MessageCount, sess.Summary, sess.CreatedAt, time.Now(),
	)
	return err
}

// Load retrieves a session by ID.
func (s *PostgresStore) Load(ctx context.Context, id string) (*session.SessionState, error) {
	query := `
		SELECT id, user_id, syllabus_id, topic_id, topic_name, deviation_stack, message_count, summary, created_at, updated_at
		FROM sessions WHERE id = $1
	`
	row := s.db.QueryRowContext(ctx, query, id)

	var sess session.SessionState
	err := row.Scan(
		&sess.ID,
		&sess.UserID,
		&sess.SyllabusID,
		&sess.TopicID,
		&sess.TopicName,
		&sess.DeviationStack,
		&sess.MessageCount,
		&sess.Summary,
		&sess.CreatedAt,
		&sess.UpdatedAt,
	)
	if err == sql.ErrNoRows {
		return nil, nil // not found
	}
	if err != nil {
		return nil, err
	}
	return &sess, nil
}
