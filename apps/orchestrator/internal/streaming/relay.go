package streaming

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strings"
	"time"
)

// Relay connects to the FastAPI SSE endpoint and forwards events to
// the WebSocket hub for the given session.
type Relay struct {
	fastapiURL string
	hub        *Hub
}

// NewRelay creates a Relay pointing to the FastAPI service URL.
func NewRelay(fastapiURL string) *Relay {
	return &Relay{
		fastapiURL: fastapiURL,
		hub:        GetHub(),
	}
}

// RelaySession forwards FastAPI SSE events for a session to WebSocket clients.
// It calls POST /api/v1/sessions/:id/messages on FastAPI and streams the response.
func (relay *Relay) RelaySession(
	ctx context.Context,
	sessionID string,
	authToken string,
	requestBody io.Reader,
) error {
	url := fmt.Sprintf("%s/api/v1/sessions/%s/messages", relay.fastapiURL, sessionID)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, requestBody)
	if err != nil {
		return fmt.Errorf("relay: build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+authToken)
	req.Header.Set("Accept", "text/event-stream")

	client := &http.Client{Timeout: 120 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("relay: do request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("relay: FastAPI returned %d", resp.StatusCode)
	}

	// Read SSE events line by line and broadcast to WebSocket clients
	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "data: ") {
			continue
		}
		data := strings.TrimPrefix(line, "data: ")
		relay.hub.Broadcast(sessionID, []byte("data: "+data+"\n\n"))
	}

	if err := scanner.Err(); err != nil && err != io.EOF {
		slog.Error("relay.scan_error", "session_id", sessionID, "error", err)
		return err
	}

	slog.Info("relay.complete", "session_id", sessionID)
	return nil
}
