package gphoto

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/lib/pq"
	"github.com/rclone/rclone/fs"
)

const (
	// NotifyChannel is the PostgreSQL channel name for media changes
	NotifyChannel = "media_changes"

	// Reconnect timing for listener
	minReconnectInterval = 10 * time.Second
	maxReconnectInterval = time.Minute
)

// MediaChangeEvent represents a notification payload from PostgreSQL
type MediaChangeEvent struct {
	Action   string `json:"action"`    // INSERT, UPDATE, DELETE
	UserName string `json:"user_name"` // User who owns the media
	MediaKey string `json:"media_key"` // Media key affected
	Path     string `json:"path"`      // File path (for cache invalidation)
	OldPath  string `json:"old_path"`  // Previous path (for UPDATE operations, to invalidate old cache)
}

// NotifyListener manages PostgreSQL LISTEN/NOTIFY for real-time updates
type NotifyListener struct {
	listener    *pq.Listener
	connStr     string
	user        string
	eventChan   chan MediaChangeEvent
	stopChan    chan struct{}
	stopOnce    sync.Once
	mu          sync.RWMutex // Protects isListening
	isListening bool
}

// NewNotifyListener creates a new PostgreSQL notification listener
func NewNotifyListener(connStr, user string) *NotifyListener {
	return &NotifyListener{
		connStr:   connStr,
		user:      user,
		eventChan: make(chan MediaChangeEvent, 10000), // Large buffer for bulk operations
		stopChan:  make(chan struct{}),
	}
}

// Start begins listening for notifications
func (nl *NotifyListener) Start(ctx context.Context) error {
	// Create event callback for connection events
	eventCallback := func(ev pq.ListenerEventType, err error) {
		switch ev {
		case pq.ListenerEventConnected:
			fs.Debugf(nil, "pg_notify: connected to PostgreSQL")
		case pq.ListenerEventDisconnected:
			fs.Errorf(nil, "pg_notify: disconnected from PostgreSQL: %v", err)
		case pq.ListenerEventReconnected:
			fs.Debugf(nil, "pg_notify: reconnected to PostgreSQL")
		case pq.ListenerEventConnectionAttemptFailed:
			fs.Errorf(nil, "pg_notify: connection attempt failed: %v", err)
		}
	}

	// Create listener
	nl.listener = pq.NewListener(nl.connStr, minReconnectInterval, maxReconnectInterval, eventCallback)

	// Subscribe to channel
	if err := nl.listener.Listen(NotifyChannel); err != nil {
		nl.listener.Close()
		return fmt.Errorf("failed to listen on channel %s: %w", NotifyChannel, err)
	}

	nl.mu.Lock()
	nl.isListening = true
	nl.mu.Unlock()
	fs.Debugf(nil, "pg_notify: listening on channel '%s' for user '%s'", NotifyChannel, nl.user)

	// Start processing notifications in background
	go nl.processNotifications(ctx)

	return nil
}

// processNotifications handles incoming notifications
func (nl *NotifyListener) processNotifications(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			fs.Debugf(nil, "pg_notify: context cancelled, stopping listener")
			return
		case <-nl.stopChan:
			fs.Debugf(nil, "pg_notify: stop signal received")
			return
		case notification := <-nl.listener.Notify:
			if notification == nil {
				// Connection lost, pq.Listener will reconnect automatically
				continue
			}

			// Parse the JSON payload
			var event MediaChangeEvent
			if err := json.Unmarshal([]byte(notification.Extra), &event); err != nil {
				fs.Errorf(nil, "pg_notify: failed to parse notification: %v", err)
				continue
			}

			// Filter by user - only process events for our user
			if event.UserName != nl.user {
				fs.Debugf(nil, "pg_notify: ignoring event for user '%s' (we are '%s')", event.UserName, nl.user)
				continue
			}

			fs.Debugf(nil, "pg_notify: received %s event for media_key '%s'", event.Action, event.MediaKey)

			// Send to event channel (non-blocking)
			select {
			case nl.eventChan <- event:
			default:
				fs.Errorf(nil, "pg_notify: event channel full, dropping event")
			}
		case <-time.After(90 * time.Second):
			// Ping to keep connection alive
			go func() {
				if err := nl.listener.Ping(); err != nil {
					fs.Errorf(nil, "pg_notify: ping failed: %v", err)
				}
			}()
		}
	}
}

// Events returns the channel for receiving filtered events
func (nl *NotifyListener) Events() <-chan MediaChangeEvent {
	return nl.eventChan
}

// Stop stops the listener
func (nl *NotifyListener) Stop() error {
	var err error
	nl.stopOnce.Do(func() {
		nl.mu.Lock()
		wasListening := nl.isListening
		nl.isListening = false
		nl.mu.Unlock()

		if !wasListening {
			return
		}

		close(nl.stopChan)

		if nl.listener != nil {
			if unlErr := nl.listener.Unlisten(NotifyChannel); unlErr != nil {
				fs.Errorf(nil, "pg_notify: failed to unlisten: %v", unlErr)
			}
			err = nl.listener.Close()
		}
	})
	return err
}

// IsListening returns whether the listener is currently active
func (nl *NotifyListener) IsListening() bool {
	nl.mu.RLock()
	defer nl.mu.RUnlock()
	return nl.isListening
}

// CreateNotifyFunctionSQL returns the SQL to create/update the notification function
// This uses CREATE OR REPLACE so it can be called on every mount to update the function
func CreateNotifyFunctionSQL() string {
	return fmt.Sprintf(`
-- Create or replace the notification function
CREATE OR REPLACE FUNCTION notify_media_changes()
RETURNS TRIGGER AS $$
DECLARE
    payload JSON;
    affected_user TEXT;
    affected_key TEXT;
    affected_path TEXT;
    old_path TEXT;
BEGIN
    -- Determine which row to use based on operation
    IF TG_OP = 'DELETE' THEN
        affected_user := OLD.user_name;
        affected_key := OLD.media_key;
        affected_path := COALESCE(OLD.path, '');
        old_path := '';
    ELSIF TG_OP = 'UPDATE' THEN
        affected_user := NEW.user_name;
        affected_key := NEW.media_key;
        affected_path := COALESCE(NEW.path, '');
        old_path := COALESCE(OLD.path, '');
    ELSE
        -- INSERT
        affected_user := NEW.user_name;
        affected_key := NEW.media_key;
        affected_path := COALESCE(NEW.path, '');
        old_path := '';
    END IF;

    -- Build JSON payload (includes both paths for cache invalidation on UPDATE)
    payload := json_build_object(
        'action', TG_OP,
        'user_name', affected_user,
        'media_key', affected_key,
        'path', affected_path,
        'old_path', old_path
    );

    -- Send notification
    PERFORM pg_notify('%s', payload::text);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
`, NotifyChannel)
}

// CreateNotifyTriggerOnlySQL returns the SQL to create just the trigger (assumes function exists)
func CreateNotifyTriggerOnlySQL(tableName string) string {
	return fmt.Sprintf(`
-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS media_changes_trigger ON %s;

-- Create trigger for INSERT, UPDATE, DELETE
CREATE TRIGGER media_changes_trigger
AFTER INSERT OR UPDATE OR DELETE ON %s
FOR EACH ROW EXECUTE FUNCTION notify_media_changes();
`, tableName, tableName)
}

// CreateNotifyTriggerSQL returns the SQL to create both function and trigger
// Kept for backwards compatibility
func CreateNotifyTriggerSQL(tableName string) string {
	return CreateNotifyFunctionSQL() + CreateNotifyTriggerOnlySQL(tableName)
}

