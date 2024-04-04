package main

import (
"fmt"
"log/slog"
"net/http"
"os"

"github.com/go-chi/chi/v5"
"github.com/go-chi/chi/v5/middleware"
)

func main() {
port := os.Getenv("PORT")
if port == "" {
port = "8080"
}

r := chi.NewRouter()
r.Use(middleware.Logger)
r.Use(middleware.Recoverer)
r.Use(middleware.RequestID)

r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
w.Write([]byte({"status":"ok","service":"syl-orchestrator"}))
})

// Session routes
r.Route("/api/v1/sessions", func(r chi.Router) {
r.Post("/", createSession)
r.Get("/{id}", getSession)
r.Post("/{id}/messages", sendMessage)
r.Post("/{id}/resume", resumeDeviation)
r.Get("/{id}/progress", getProgress)
})

// WebSocket
r.Get("/ws/{sessionId}", handleWebSocket)

slog.Info("orchestrator starting", "port", port)
if err := http.ListenAndServe(":"+port, r); err != nil {
fmt.Fprintf(os.Stderr, "server error: %v\n", err)
os.Exit(1)
}
}

// Stub handlers
func createSession(w http.ResponseWriter, r *http.Request)   { w.Write([]byte("{}")) }
func getSession(w http.ResponseWriter, r *http.Request)      { w.Write([]byte("{}")) }
func sendMessage(w http.ResponseWriter, r *http.Request)     { w.Write([]byte("{}")) }
func resumeDeviation(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{}")) }
func getProgress(w http.ResponseWriter, r *http.Request)     { w.Write([]byte("{}")) }
func handleWebSocket(w http.ResponseWriter, r *http.Request) {}
