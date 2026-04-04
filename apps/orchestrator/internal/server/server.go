package server

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

// Server holds the HTTP server and all dependencies.
type Server struct {
	router *chi.Mux
	port   string
	logger *slog.Logger
}

// New creates a configured Server instance.
func New() *Server {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	s := &Server{
		router: chi.NewRouter(),
		port:   port,
		logger: slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo})),
	}
	s.mountMiddleware()
	s.mountRoutes()
	return s
}

func (s *Server) mountMiddleware() {
	s.router.Use(middleware.RequestID)
	s.router.Use(middleware.RealIP)
	s.router.Use(loggingMiddleware(s.logger))
	s.router.Use(middleware.Recoverer)
	s.router.Use(corsMiddleware)
}

// ListenAndServe starts the HTTP server.
func (s *Server) ListenAndServe() error {
	s.logger.Info("orchestrator starting", "port", s.port)
	srv := &http.Server{
		Addr:         ":" + s.port,
		Handler:      s.router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 120 * time.Second,
		IdleTimeout:  60 * time.Second,
	}
	return srv.ListenAndServe()
}

// writeJSON writes a JSON response with the given status code.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		slog.Error("writeJSON failed", "error", err)
	}
}

// writeError writes a standard error JSON response.
func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
