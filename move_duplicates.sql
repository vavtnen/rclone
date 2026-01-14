-- Run with: psql "your_connection_string" -f move_duplicates.sql

BEGIN;

-- Preview: Show what will be moved
SELECT
    user_name,
    file_name,
    name,
    path,
    COUNT(*) as duplicate_count,
    ARRAY_AGG(media_key) as media_keys
FROM remote_media
WHERE type >= 0
GROUP BY user_name, file_name, name, path
HAVING COUNT(*) > 1
ORDER BY user_name, duplicate_count DESC;

-- Move duplicates to root (keeps first one in place)
WITH duplicates AS (
    SELECT
        media_key,
        ROW_NUMBER() OVER (
            PARTITION BY user_name, file_name, name, path
            ORDER BY media_key
        ) as rn
    FROM remote_media
    WHERE type >= 0
)
UPDATE remote_media
SET path = NULL
WHERE media_key IN (
    SELECT media_key
    FROM duplicates
    WHERE rn > 1
);

-- Show how many rows were updated
-- Now review the results above, then:
--   COMMIT;   -- to save changes
--   ROLLBACK; -- to undo changes
