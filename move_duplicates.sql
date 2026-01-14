-- =============================================================================
-- STEP 1: PREVIEW - Find all duplicate files per user
-- Run this first to see what will be affected
-- =============================================================================

SELECT
    user_name,
    file_name,
    name,
    path,
    COUNT(*) as duplicate_count,
    ARRAY_AGG(media_key) as media_keys
FROM remote_media
WHERE type >= 0  -- Only files, not folders
GROUP BY user_name, file_name, name, path
HAVING COUNT(*) > 1
ORDER BY user_name, duplicate_count DESC;

-- =============================================================================
-- STEP 2: UPDATE - Move duplicates to root (path = NULL)
-- Uncomment and run after reviewing the preview above
-- Keeps first occurrence in place, moves extras to root
-- =============================================================================

-- WITH duplicates AS (
--     SELECT
--         media_key,
--         ROW_NUMBER() OVER (
--             PARTITION BY user_name, file_name, name, path
--             ORDER BY media_key
--         ) as rn
--     FROM remote_media
--     WHERE type >= 0
-- )
-- UPDATE remote_media
-- SET path = NULL
-- WHERE media_key IN (
--     SELECT media_key
--     FROM duplicates
--     WHERE rn > 1
-- );
