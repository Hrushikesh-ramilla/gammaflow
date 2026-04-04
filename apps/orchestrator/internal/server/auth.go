package server

import (
	"context"
	"errors"
	"os"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

type contextKey string

const userIDKey contextKey = "user_id"

// withUserID attaches a user_id to the context.
func withUserID(ctx context.Context, userID string) context.Context {
	return context.WithValue(ctx, userIDKey, userID)
}

// getUserID retrieves the user_id from context set by authMiddleware.
func getUserID(ctx context.Context) (string, bool) {
	v, ok := ctx.Value(userIDKey).(string)
	return v, ok && v != ""
}

// validateJWT decodes and validates a HS256 JWT, returning the subject (user_id).
func validateJWT(tokenStr, secret string) (string, error) {
	token, err := jwt.Parse(tokenStr, func(t *jwt.Token) (any, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, errors.New("unexpected signing method")
		}
		return []byte(secret), nil
	})
	if err != nil || !token.Valid {
		return "", errors.New("invalid token")
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return "", errors.New("invalid claims")
	}

	sub, err := claims.GetSubject()
	if err != nil || sub == "" {
		return "", errors.New("missing subject")
	}

	// Check expiry
	exp, err := claims.GetExpirationTime()
	if err == nil && exp != nil && exp.Before(time.Now()) {
		return "", errors.New("token expired")
	}

	return sub, nil
}

// getJWTSecret returns the JWT secret from environment.
func getJWTSecret() string {
	s := os.Getenv("JWT_SECRET")
	if s == "" {
		return "change_me_in_production_minimum_32_chars"
	}
	return s
}
