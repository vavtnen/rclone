package mediavfs

import (
	"context"
	"fmt"
	"strings"

	"github.com/rclone/rclone/backend/mediavfs/gphoto"
	"github.com/rclone/rclone/fs"
)

// SetupNotifyTrigger creates the PostgreSQL trigger for notifications
// Uses advisory lock to prevent "tuple concurrently updated" errors when
// multiple instances start simultaneously
func (f *Fs) SetupNotifyTrigger(ctx context.Context) error {
	// Check if function exists and has the expected payload fields
	// This avoids unnecessary updates when multiple mounts are running
	var funcSource string
	funcCheckSQL := `SELECT COALESCE(prosrc, '') FROM pg_proc WHERE proname = 'notify_media_changes'`
	if err := f.db.QueryRowContext(ctx, funcCheckSQL).Scan(&funcSource); err == nil {
		// Function exists - check if it has all required fields (path is the newest)
		if strings.Contains(funcSource, "'path'") {
			fs.Debugf(f, "PostgreSQL notify function already up-to-date")
		} else {
			// Function exists but outdated - update it
			fs.Debugf(f, "Updating PostgreSQL notify function to include path field")
			functionSQL := gphoto.CreateNotifyFunctionSQL()
			if _, err := f.db.ExecContext(ctx, functionSQL); err != nil {
				return fmt.Errorf("failed to update notify function: %w", err)
			}
		}
	} else {
		// Function doesn't exist - create it
		functionSQL := gphoto.CreateNotifyFunctionSQL()
		if _, err := f.db.ExecContext(ctx, functionSQL); err != nil {
			return fmt.Errorf("failed to create notify function: %w", err)
		}
	}

	// Check if trigger already exists
	var exists bool
	checkSQL := `SELECT EXISTS (
		SELECT 1 FROM pg_trigger
		WHERE tgname = 'media_changes_trigger'
	)`
	if err := f.db.QueryRowContext(ctx, checkSQL).Scan(&exists); err != nil {
		return fmt.Errorf("failed to check trigger existence: %w", err)
	}

	if exists {
		fs.Debugf(f, "PostgreSQL notify trigger already exists on table '%s', function updated", f.opt.TableName)
		return nil
	}

	// Use advisory lock to prevent concurrent trigger creation
	// Lock ID is a hash of the trigger name
	lockSQL := `SELECT pg_advisory_lock(hashtext('media_changes_trigger_setup'))`
	if _, err := f.db.ExecContext(ctx, lockSQL); err != nil {
		return fmt.Errorf("failed to acquire advisory lock: %w", err)
	}
	defer func() {
		unlockSQL := `SELECT pg_advisory_unlock(hashtext('media_changes_trigger_setup'))`
		f.db.ExecContext(ctx, unlockSQL)
	}()

	// Check again after acquiring lock (another instance may have created it)
	if err := f.db.QueryRowContext(ctx, checkSQL).Scan(&exists); err != nil {
		return fmt.Errorf("failed to check trigger existence: %w", err)
	}
	if exists {
		fs.Debugf(f, "PostgreSQL notify trigger created by another instance")
		return nil
	}

	// Create the trigger (function already exists)
	triggerSQL := gphoto.CreateNotifyTriggerOnlySQL(f.opt.TableName)
	if _, err := f.db.ExecContext(ctx, triggerSQL); err != nil {
		return fmt.Errorf("failed to create notify trigger: %w", err)
	}
	fs.Debugf(f, "Created PostgreSQL notify trigger on table '%s'", f.opt.TableName)
	return nil
}
