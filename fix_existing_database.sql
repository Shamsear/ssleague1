-- =============================================================================
-- FIX EXISTING DATABASE - ADD MISSING UPDATED_AT COLUMN
-- =============================================================================
-- This script fixes the existing database by adding the missing updated_at 
-- column to the user table so the trigger works properly
-- =============================================================================

-- Add the missing updated_at column to the user table
ALTER TABLE "user" 
ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Update the trigger function to handle the profile_updated_at field properly
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    -- Also update profile_updated_at if it exists
    IF TG_TABLE_NAME = 'user' THEN
        NEW.profile_updated_at = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Now you can safely update the user password
UPDATE "user"
SET password_hash = 'scrypt:32768:8:1$DPINGnNtClvI0mKL$5fda26eaea02e0016beac6e536d2c581f0f587760267d634644a86e21ac17ffcc9f6baeb4a6d4ce35fa14d71a64da0d8a66f6765bbb917cbe5713befef8b691f'
WHERE id = 1;

-- Verify the fix worked
SELECT id, username, email, is_admin, is_approved, created_at, updated_at 
FROM "user" 
WHERE id = 1;