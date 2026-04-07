package streaming

import "encoding/json"

// EventType identifies the type of a streaming event.
type EventType string

const (
	EventToken           EventType = "token"
	EventCitation        EventType = "citation"
	EventProviderSwitch  EventType = "provider_switched"
	EventDeviation       EventType = "deviation"
	EventResume          EventType = "resume"
	EventComplete        EventType = "complete"
	EventError           EventType = "error"
	EventProcessingPage  EventType = "page_processed"
	EventPing            EventType = "ping"
)

// Event is the base structure for all streaming events sent to the frontend.
type Event struct {
	Type EventType `json:"type"`
	Data any       `json:"data,omitempty"`
}

// TokenEvent carries a single LLM token.
type TokenEvent struct {
	Content  string `json:"content"`
	Provider string `json:"provider"`
}

// CitationEvent carries a citation reference for PDF autoscroll.
type CitationEvent struct {
	Page       int    `json:"page"`
	Document   string `json:"doc"`
	SourceType string `json:"source"` // "PDF" | "OCR"
	CharStart  *int   `json:"char_start,omitempty"`
	CharEnd    *int   `json:"char_end,omitempty"`
}

// ProviderSwitchEvent signals a fallback to another LLM provider.
type ProviderSwitchEvent struct {
	From   string `json:"from"`
	To     string `json:"to"`
	Reason string `json:"reason"`
}

// DeviationEvent signals that the user went off-topic.
type DeviationEvent struct {
	Depth     int    `json:"depth"`
	Topic     string `json:"topic"`
	MessageAt int    `json:"message_at"`
}

// CompleteEvent signals the end of a streaming response.
type CompleteEvent struct {
	Provider   string `json:"provider"`
	TokensUsed int    `json:"tokens_used"`
	MessageID  string `json:"message_id"`
	Cached     bool   `json:"cached,omitempty"`
}

// ErrorEvent signals a streaming error.
type ErrorEvent struct {
	Message string `json:"message"`
}

// SSELine formats an event as an SSE data line.
func SSELine(eventType EventType, payload any) []byte {
	data := map[string]any{"type": string(eventType)}

	// Flatten payload into the top-level map
	if payload != nil {
		b, _ := json.Marshal(payload)
		var m map[string]any
		if err := json.Unmarshal(b, &m); err == nil {
			for k, v := range m {
				data[k] = v
			}
		}
	}

	b, _ := json.Marshal(data)
	return []byte("data: " + string(b) + "\n\n")
}
