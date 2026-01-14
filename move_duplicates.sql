-- =============================================================================
-- Move Duplicate Files to Root
--
-- Finds files with same (user_name, file_name, path) and moves the OLDER ones
-- (by server_creation_timestamp) to root (path = NULL). The newest file stays.
--
-- Run with: psql "your_connection_string" -f move_duplicates.sql
-- Then type COMMIT to save or ROLLBACK to undo.
-- =============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: PREVIEW - Show duplicates that will be moved
-- =============================================================================

SELECT
    'WILL MOVE TO ROOT' as action,
    user_name,
    file_name,
    path as current_path,
    media_key,
    size_bytes,
    to_timestamp(server_creation_timestamp / 1000) as created_at,
    rn as duplicate_number
FROM (
    SELECT
        user_name,
        file_name,
        path,
        media_key,
        size_bytes,
        server_creation_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY user_name, file_name, path
            ORDER BY server_creation_timestamp DESC
        ) as rn
    FROM remote_media
    WHERE type >= 0  -- Only files, not folders
    AND (trash_timestamp IS NULL OR trash_timestamp >= 0)  -- Not hidden/trashed
) ranked
WHERE rn > 1  -- Only duplicates (not the newest)
ORDER BY user_name, file_name, path, rn;

-- =============================================================================
-- STEP 2: UPDATE - Move older duplicates to root (path = NULL)
-- =============================================================================

WITH ranked AS (
    SELECT
        media_key,
        ROW_NUMBER() OVER (
            PARTITION BY user_name, file_name, path
            ORDER BY server_creation_timestamp DESC
        ) as rn
    FROM remote_media
    WHERE type >= 0
    AND (trash_timestamp IS NULL OR trash_timestamp >= 0)
)
UPDATE remote_media
SET path = NULL
WHERE media_key IN (
    SELECT media_key
    FROM ranked
    WHERE rn > 1
);

-- Show count of affected rows
-- Then review above and type:
--   COMMIT;   -- to save changes
--   ROLLBACK; -- to undo changes
