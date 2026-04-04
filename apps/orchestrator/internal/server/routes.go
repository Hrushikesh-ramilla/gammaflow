package server

import (
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/syl/orchestrator/internal/deviation"
	"github.com/syl/orchestrator/internal/intent"
	"github.com/syl/orchestrator/internal/session"
	"github.com/syl/orchestrator/internal/streaming"
)

// mountRoutes registers all API routes.
func (s *Server) mountRoutes() {
	r := s.router

	// Health check
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, 200, map[string]string{"status": "ok", "service": "syl-orchestrator"})
	})

	// Session routes
	r.Route("/api/v1/sessions", func(r chi.Router) {
		r.Use(authMiddleware)

		mgr := session.NewManager()
		deviationSvc := deviation.NewService()
		classifierSvc := intent.NewClassifier()

		r.Post("/", mgr.HandleCreate)
		r.Get("/{id}", mgr.HandleGet)
		r.Post("/{id}/messages", func(w http.ResponseWriter, req *http.Request) {
			mgr.HandleMessage(w, req, classifierSvc, deviationSvc)
		})
		r.Post("/{id}/resume", func(w http.ResponseWriter, req *http.Request) {
			deviationSvc.HandleResume(w, req)
		})
		r.Get("/{id}/progress", mgr.HandleProgress)
	})

	// WebSocket streaming
	r.Get("/ws/{sessionId}", func(w http.ResponseWriter, r *http.Request) {
		hub := streaming.GetHub()
		hub.HandleWebSocket(w, r)
	})

	// Progress tracking
	r.Route("/api/v1/progress", func(r chi.Router) {
		r.Use(authMiddleware)
		r.Get("/{syllabusId}", func(w http.ResponseWriter, req *http.Request) {
			mgr := session.NewManager()
			mgr.HandleGetProgress(w, req)
		})
		r.Patch("/{topicId}", func(w http.ResponseWriter, req *http.Request) {
			mgr := session.NewManager()
			mgr.HandleUpdateProgress(w, req)
		})
	})
}
