package claude

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

const (
	anthropicAPIURL   = "https://api.anthropic.com/v1/messages"
	anthropicVersion  = "2023-06-01"
	defaultHaikuModel = "claude-3-haiku-20240307"
)

// Client is a minimal Claude API client for non-streaming completions.
// Used by the intent classifier and session summary generator.
type Client struct {
	apiKey     string
	httpClient *http.Client
}

// request is the Anthropic messages API request body.
type request struct {
	Model     string    `json:"model"`
	MaxTokens int       `json:"max_tokens"`
	Messages  []message `json:"messages"`
}

type message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// response is the relevant subset of the Anthropic API response.
type response struct {
	Content []struct {
		Text string `json:"text"`
	} `json:"content"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

// NewClient creates a Claude API client using ANTHROPIC_API_KEY from env.
func NewClient() *Client {
	return &Client{
		apiKey: os.Getenv("ANTHROPIC_API_KEY"),
		httpClient: &http.Client{
			Timeout: 15 * time.Second,
		},
	}
}

// CompleteHaiku sends a single-turn prompt to Claude Haiku and returns the text response.
func (c *Client) CompleteHaiku(ctx context.Context, prompt string) (string, error) {
	return c.complete(ctx, defaultHaikuModel, prompt, 512)
}

// complete is the internal completion method.
func (c *Client) complete(ctx context.Context, model, prompt string, maxTokens int) (string, error) {
	if c.apiKey == "" {
		return "", fmt.Errorf("claude: ANTHROPIC_API_KEY not set")
	}

	body := request{
		Model:     model,
		MaxTokens: maxTokens,
		Messages:  []message{{Role: "user", Content: prompt}},
	}

	b, err := json.Marshal(body)
	if err != nil {
		return "", fmt.Errorf("claude: marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, anthropicAPIURL, bytes.NewReader(b))
	if err != nil {
		return "", fmt.Errorf("claude: build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", c.apiKey)
	req.Header.Set("anthropic-version", anthropicVersion)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("claude: http do: %w", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("claude: read body: %w", err)
	}

	var apiResp response
	if err := json.Unmarshal(raw, &apiResp); err != nil {
		return "", fmt.Errorf("claude: parse response: %w", err)
	}

	if apiResp.Error != nil {
		return "", fmt.Errorf("claude API error: %s", apiResp.Error.Message)
	}

	if len(apiResp.Content) == 0 {
		return "", fmt.Errorf("claude: empty response content")
	}

	return apiResp.Content[0].Text, nil
}
