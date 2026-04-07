package streaming

import (
	"log/slog"
	"net/http"
	"sync"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin:     func(r *http.Request) bool { return true },
	ReadBufferSize:  1024,
	WriteBufferSize: 4096,
}

// Hub manages active WebSocket connections per session.
type Hub struct {
	mu    sync.RWMutex
	conns map[string][]*websocket.Conn // sessionID → connections
}

var globalHub = &Hub{
	conns: make(map[string][]*websocket.Conn),
}

// GetHub returns the singleton WebSocket hub.
func GetHub() *Hub {
	return globalHub
}

// HandleWebSocket upgrades the HTTP connection and maintains it until disconnection.
func (h *Hub) HandleWebSocket(w http.ResponseWriter, r *http.Request) {
	sessionID := chi.URLParam(r, "sessionId")

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		slog.Error("ws.upgrade_failed", "error", err)
		return
	}
	defer func() {
		h.remove(sessionID, conn)
		conn.Close()
	}()

	h.add(sessionID, conn)
	slog.Info("ws.client_connected", "session_id", sessionID)

	// Heartbeat loop — sends ping every 30s to keep alive
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	done := make(chan struct{})
	go func() {
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				close(done)
				return
			}
		}
	}()

	for {
		select {
		case <-done:
			slog.Info("ws.client_disconnected", "session_id", sessionID)
			return
		case <-ticker.C:
			if err := conn.WriteMessage(
				websocket.TextMessage,
				SSELine(EventPing, nil),
			); err != nil {
				return
			}
		}
	}
}

// Broadcast sends an event to all WebSocket clients for a session.
func (h *Hub) Broadcast(sessionID string, line []byte) {
	h.mu.RLock()
	conns := h.conns[sessionID]
	h.mu.RUnlock()

	dead := []*websocket.Conn{}
	for _, conn := range conns {
		if err := conn.WriteMessage(websocket.TextMessage, line); err != nil {
			dead = append(dead, conn)
		}
	}
	for _, c := range dead {
		h.remove(sessionID, c)
		c.Close()
	}
}

func (h *Hub) add(sessionID string, conn *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.conns[sessionID] = append(h.conns[sessionID], conn)
}

func (h *Hub) remove(sessionID string, conn *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()
	list := h.conns[sessionID]
	for i, c := range list {
		if c == conn {
			h.conns[sessionID] = append(list[:i], list[i+1:]...)
			break
		}
	}
}
