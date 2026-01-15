-- =============================================================================
-- QUERY 1: PREVIEW - View duplicates that will be moved
-- Run this first to see what will be affected
-- =============================================================================

SELECT
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
    WHERE type >= 0
    AND (trash_timestamp IS NULL OR trash_timestamp >= 0)
) ranked
WHERE rn > 1
ORDER BY user_name, file_name, path, rn;


-- =============================================================================
-- QUERY 2: UPDATE - Move older duplicates to root (path = NULL)
-- Run this AFTER reviewing the preview above
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
