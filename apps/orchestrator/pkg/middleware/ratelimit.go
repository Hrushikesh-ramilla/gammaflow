package middleware

import (
	"net/http"
	"sync"
	"time"
)

// Free tier limits based on syl.md blueprint (Commit 195)
const (
	MaxMessagesPerDay = 50
	MaxTokensPerMin   = 10000
)

type userUsage struct {
	MessageCount int
	LastReset    time.Time
}

var (
	// In-memory simplistic rate limiter for MVP
	// In production, this would be backed by Redis.
	usageStore = make(map[string]*userUsage)
	usageMutex sync.Mutex
)

// RateLimit implements the free tier enforcement middleware.
func RateLimit(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Assuming Auth middleware has already run and set the user ID in context
		userID, ok := r.Context().Value("user_id").(string)
		if !ok || userID == "" {
			// If no user context, just pass (could be public route)
			next.ServeHTTP(w, r)
			return
		}

		// Only rate limit specific endpoints like sending messages
		if r.Method == http.MethodPost && r.URL.Path == "/api/sessions/message" {
			usageMutex.Lock()
			usage, exists := usageStore[userID]
			
			// Reset daily
			if !exists || time.Since(usage.LastReset) > 24*time.Hour {
				usage = &userUsage{
					MessageCount: 0,
					LastReset:    time.Now(),
				}
				usageStore[userID] = usage
			}

			if usage.MessageCount >= MaxMessagesPerDay {
				usageMutex.Unlock()
				http.Error(w, "Free tier limit reached: 50 messages per day. Please upgrade to continue studying.", http.StatusTooManyRequests)
				return
			}

			usage.MessageCount++
			usageMutex.Unlock()
		}

		next.ServeHTTP(w, r)
	})
}
