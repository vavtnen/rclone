package mediavfs

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/rclone/rclone/backend/mediavfs/gphoto"
	"github.com/rclone/rclone/fs"
)

// UnsupportedVideosState represents the sync state for unsupported videos
type UnsupportedVideosState struct {
	PageToken    string
	SyncComplete bool
	LastSync     int64
}

// GetUnsupportedVideosState retrieves the unsupported videos sync state for the current user
func (f *Fs) GetUnsupportedVideosState(ctx context.Context) (*UnsupportedVideosState, error) {
	var state UnsupportedVideosState
	var pageToken sql.NullString
	var lastSync sql.NullInt64

	err := f.db.QueryRowContext(ctx, `
		SELECT page_token, sync_complete, last_sync
		FROM unsupported_videos_state
		WHERE user_name = $1
	`, f.opt.User).Scan(&pageToken, &state.SyncComplete, &lastSync)

	if err == sql.ErrNoRows {
		// Create initial state for this user
		_, err = f.db.ExecContext(ctx, `
			INSERT INTO unsupported_videos_state (user_name, page_token, sync_complete, last_sync)
			VALUES ($1, '', FALSE, 0)
			ON CONFLICT (user_name) DO NOTHING
		`, f.opt.User)
		if err != nil {
			return nil, fmt.Errorf("failed to create initial unsupported videos state: %w", err)
		}
		return &UnsupportedVideosState{
			PageToken:    "",
			SyncComplete: false,
			LastSync:     0,
		}, nil
	}

	if err != nil {
		return nil, fmt.Errorf("failed to get unsupported videos state: %w", err)
	}

	if pageToken.Valid {
		state.PageToken = pageToken.String
	}
	if lastSync.Valid {
		state.LastSync = lastSync.Int64
	}

	return &state, nil
}

// UpdateUnsupportedVideosState updates the unsupported videos sync state for the current user
func (f *Fs) UpdateUnsupportedVideosState(ctx context.Context, pageToken string, syncComplete bool) error {
	lastSync := time.Now().Unix()
	_, err := f.db.ExecContext(ctx, `
		UPDATE unsupported_videos_state
		SET page_token = $1, sync_complete = $2, last_sync = $3
		WHERE user_name = $4
	`, pageToken, syncComplete, lastSync, f.opt.User)

	if err != nil {
		return fmt.Errorf("failed to update unsupported videos state: %w", err)
	}

	return nil
}

// UpsertUnsupportedVideos inserts or updates multiple unsupported videos in the database
// These are files that don't appear in the regular library sync but have direct download URLs
func (f *Fs) UpsertUnsupportedVideos(ctx context.Context, videos []gphoto.UnsupportedVideoItem) error {
	if len(videos) == 0 {
		return nil
	}

	tx, err := f.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("failed to start transaction: %w", err)
	}
	defer tx.Rollback()

	for _, video := range videos {
		// Determine type based on filename: VTT files vs actual videos
		mediaType := 1 // Default to video type
		if strings.HasSuffix(video.FileName, "_thumbs.vtt") {
			mediaType = 99 // Use a special type for VTT metadata files
		}

		// Insert or update the video entry
		// - Use media_key as the unique identifier
		// - Store download URL in remote_url column
		// - Set trash_timestamp = 0 to make it visible
		// - Place files in "Unsupported Videos" folder
		query := fmt.Sprintf(`
			INSERT INTO %s (
				media_key, file_name, name, path, size_bytes, utc_timestamp,
				remote_url, trash_timestamp, type, user_name
			) VALUES ($1, $2, '', 'Unsupported Videos', $3, $4, $5, 0, $6, $7)
			ON CONFLICT (media_key) DO UPDATE SET
				file_name = EXCLUDED.file_name,
				size_bytes = EXCLUDED.size_bytes,
				remote_url = EXCLUDED.remote_url,
				trash_timestamp = 0
		`, f.opt.TableName)

		_, err := tx.ExecContext(ctx, query,
			video.MediaKey,
			video.FileName,
			video.Size,
			video.Timestamp/1000, // Convert ms to seconds
			video.DownloadURL,
			mediaType,
			f.opt.User,
		)
		if err != nil {
			return fmt.Errorf("failed to upsert unsupported video %s: %w", video.MediaKey, err)
		}
	}

	if err = tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit transaction: %w", err)
	}

	return nil
}

// SyncUnsupportedVideosNew syncs unsupported videos from Google Photos to the database
// This creates new entries for videos that aren't in the regular library
// Returns nil if web cookies are not configured (feature is optional)
// Returns error with user notification if cookies are expired
func (f *Fs) SyncUnsupportedVideosNew(ctx context.Context) error {
	// Check if web cookies are configured - this feature is optional
	session := f.GetWebSession()
	if session == nil {
		fs.Debugf(f, "Web cookies not configured, skipping unsupported videos sync (optional feature)")
		return nil
	}

	// Validate minimum required cookies
	if session.SAPISID == "" || session.SID == "" {
		fs.Debugf(f, "Required cookies (SAPISID, SID) not found in web_cookies, skipping unsupported videos sync")
		return nil
	}

	fs.Infof(f, "Starting unsupported videos sync for user %s", f.opt.User)

	// Always do a full sync for unsupported videos (no incremental API available)
	pageToken := ""
	pageNum := 1
	totalVideos := 0
	realVideos := 0

	for {
		fs.Debugf(f, "Fetching unsupported videos page %d", pageNum)

		items, nextPageToken, err := f.api.GetUnsupportedVideos(ctx, session, pageToken)
		if err != nil {
			// Check for specific error types and notify user appropriately
			if errors.Is(err, gphoto.ErrCookiesExpired) {
				fs.Errorf(f, "Web session cookies have expired. Please update web_cookies in rclone config to continue syncing unsupported videos.")
				return fmt.Errorf("cookies expired: %w", err)
			}
			if errors.Is(err, gphoto.ErrCookiesMissing) {
				fs.Infof(f, "Web cookies not fully configured. Set web_cookies in rclone config to sync unsupported videos.")
				return nil // Not an error, just skip this optional feature
			}
			return fmt.Errorf("failed to fetch page %d: %w", pageNum, err)
		}

		if len(items) == 0 {
			fs.Debugf(f, "No more videos found on page %d", pageNum)
			break
		}

		// Count real videos (not VTT files)
		for _, item := range items {
			if !strings.HasSuffix(item.FileName, "_thumbs.vtt") {
				realVideos++
			}
		}

		// Upsert videos to database
		if err := f.UpsertUnsupportedVideos(ctx, items); err != nil {
			return fmt.Errorf("failed to upsert videos: %w", err)
		}

		totalVideos += len(items)
		fs.Debugf(f, "Synced %d videos from page %d (total: %d)", len(items), pageNum, totalVideos)

		// Save progress
		if err := f.UpdateUnsupportedVideosState(ctx, nextPageToken, false); err != nil {
			fs.Errorf(f, "Failed to save progress: %v", err)
		}

		if nextPageToken == "" {
			break
		}

		pageToken = nextPageToken
		pageNum++

		// Small delay to avoid rate limiting
		time.Sleep(500 * time.Millisecond)
	}

	// Mark sync as complete
	if err := f.UpdateUnsupportedVideosState(ctx, "", true); err != nil {
		return fmt.Errorf("failed to mark sync complete: %w", err)
	}

	fs.Infof(f, "Unsupported videos sync completed: %d total entries (%d real videos)", totalVideos, realVideos)

	// Ensure "Unsupported Videos" folder exists
	if err := f.ensureUnsupportedVideosFolder(ctx); err != nil {
		fs.Errorf(f, "Failed to create Unsupported Videos folder: %v", err)
	}

	return nil
}

// ensureUnsupportedVideosFolder creates the "Unsupported Videos" folder if it doesn't exist
func (f *Fs) ensureUnsupportedVideosFolder(ctx context.Context) error {
	// Check if folder exists
	var count int
	query := fmt.Sprintf(`
		SELECT COUNT(*) FROM %s
		WHERE path = '' AND file_name = 'Unsupported Videos' AND type = -1 AND user_name = $1
	`, f.opt.TableName)

	if err := f.db.QueryRowContext(ctx, query, f.opt.User).Scan(&count); err != nil {
		return err
	}

	if count > 0 {
		return nil // Folder already exists
	}

	// Create folder
	insertQuery := fmt.Sprintf(`
		INSERT INTO %s (media_key, file_name, name, path, type, user_name)
		VALUES ($1, 'Unsupported Videos', '', '', -1, $2)
		ON CONFLICT (media_key) DO NOTHING
	`, f.opt.TableName)

	_, err := f.db.ExecContext(ctx, insertQuery, "folder:"+f.opt.User+":Unsupported Videos", f.opt.User)
	return err
}
