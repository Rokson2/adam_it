package security

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

type AuditEvent struct {
	Timestamp time.Time   `json:"timestamp"`
	EventType string      `json:"event_type"`
	EventData interface{} `json:"event_data,omitempty"`
	SessionID string      `json:"session_id,omitempty"`
	Hash      string      `json:"hash,omitempty"`
}

type Auditor struct {
	logPath string
	enabled bool
}

func NewAuditor(logPath string, enabled bool) *Auditor {
	return &Auditor{
		logPath: logPath,
		enabled: enabled,
	}
}

func (a *Auditor) Log(eventType string, eventData interface{}) error {
	return a.LogWithSession(eventType, eventData, "")
}

func (a *Auditor) LogWithSession(eventType string, eventData interface{}, sessionID string) error {
	if !a.enabled {
		return nil
	}

	dir := filepath.Dir(a.logPath)
	if err := os.MkdirAll(dir, 0700); err != nil {
		return fmt.Errorf("failed to create audit log directory: %w", err)
	}

	event := AuditEvent{
		Timestamp: time.Now().UTC(),
		EventType: eventType,
		EventData: eventData,
		SessionID: sessionID,
	}

	data, _ := json.Marshal(event)
	hash := sha256.Sum256(data)
	event.Hash = hex.EncodeToString(hash[:8])

	finalData, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal audit event: %w", err)
	}

	f, err := os.OpenFile(a.logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0600)
	if err != nil {
		return fmt.Errorf("failed to open audit log: %w", err)
	}
	defer f.Close()

	_, err = fmt.Fprintln(f, string(finalData))
	return err
}
