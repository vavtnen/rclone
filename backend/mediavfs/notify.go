package mediavfs

import (
	"context"
	"fmt"

	"github.com/rclone/rclone/backend/mediavfs/gphoto"
	"github.com/rclone/rclone/fs"
)

// SetupNotifyTrigger creates the PostgreSQL trigger for notifications
// Uses advisory lock to prevent "tuple concurrently updated" errors when
// multiple instances start simultaneously
func (f *Fs) SetupNotifyTrigger(ctx context.Context) error {
	// First check if trigger already exists
	var exists bool
	checkSQL := `SELECT EXISTS (
		SELECT 1 FROM pg_trigger
		WHERE tgname = 'media_changes_trigger'
	)`
	if err := f.db.QueryRowContext(ctx, checkSQL).Scan(&exists); err != nil {
		return fmt.Errorf("failed to check trigger existence: %w", err)
	}

	if exists {
		fs.Debugf(f, "PostgreSQL notify trigger already exists on table '%s'", f.opt.TableName)
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

	// Create the trigger
	sql := gphoto.CreateNotifyTriggerSQL(f.opt.TableName)
	_, err := f.db.ExecContext(ctx, sql)
	if err != nil {
		return fmt.Errorf("failed to create notify trigger: %w", err)
	}
	fs.Debugf(f, "Created PostgreSQL notify trigger on table '%s'", f.opt.TableName)
	return nil
}
