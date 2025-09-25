-- =============================================================================
-- MULTI-SEASON SYSTEM - MIGRATION 001
-- =============================================================================
-- Creates season management and admin invite tables
-- This is SAFE - only adding new tables, no existing data affected
-- =============================================================================

-- Season Management Table
CREATE TABLE IF NOT EXISTS season (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,                     -- "Season 16 - SS Super League"
    short_name VARCHAR(20) NOT NULL,                -- "S16"
    description TEXT,                               -- "Inaugural SS Super League Season"
    
    -- Season Status
    is_active BOOLEAN DEFAULT FALSE,                -- Only ONE active at a time
    status VARCHAR(20) DEFAULT 'upcoming',          -- upcoming, active, completed, archived
    registration_open BOOLEAN DEFAULT FALSE,        -- Teams can register for this season
    
    -- Season Configuration
    max_committee_admins INTEGER DEFAULT 15,        -- Max committee admins for system
    team_limit INTEGER,                             -- NULL = unlimited registration
    registration_deadline DATE,                     -- When team registration closes
    season_start_date DATE,                         -- When season/auctions begin
    season_end_date DATE,                           -- When season officially ends
    
    -- Timestamps
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Created by super admin
    created_by INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    
    -- Constraints
    CONSTRAINT unique_active_season CHECK (
        -- Ensure only one season can be active at a time (enforced at application level)
        TRUE  -- Application will handle this constraint
    ),
    CONSTRAINT valid_season_dates CHECK (
        season_end_date IS NULL OR season_start_date IS NULL OR season_end_date >= season_start_date
    ),
    CONSTRAINT valid_registration_deadline CHECK (
        registration_deadline IS NULL OR season_start_date IS NULL OR registration_deadline <= season_start_date
    )
);

-- Admin Invite System Table
CREATE TABLE IF NOT EXISTS admin_invite (
    id SERIAL PRIMARY KEY,
    invite_token VARCHAR(100) UNIQUE NOT NULL,      -- Unique invite link token
    
    -- Invite Configuration  
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, -- When invite expires
    max_uses INTEGER DEFAULT 1,                     -- How many people can use this invite
    current_uses INTEGER DEFAULT 0,                 -- How many times it's been used
    
    -- Tracking
    created_by INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,  -- Super admin who created
    used_by INTEGER REFERENCES "user"(id) ON DELETE SET NULL,             -- Last person who used it
    is_active BOOLEAN DEFAULT TRUE,                 -- Can still be used
    
    -- Metadata
    description TEXT,                               -- "Committee Admin Invite - January 2025"
    
    -- Timestamps
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP WITHOUT TIME ZONE,           -- When last used
    
    -- Constraints
    CONSTRAINT valid_expiry CHECK (expires_at > created_at),
    CONSTRAINT valid_uses CHECK (max_uses > 0 AND current_uses >= 0 AND current_uses <= max_uses)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_season_is_active ON season(is_active);
CREATE INDEX IF NOT EXISTS idx_season_status ON season(status);
CREATE INDEX IF NOT EXISTS idx_season_created_at ON season(created_at);

CREATE INDEX IF NOT EXISTS idx_admin_invite_token ON admin_invite(invite_token);
CREATE INDEX IF NOT EXISTS idx_admin_invite_active ON admin_invite(is_active);
CREATE INDEX IF NOT EXISTS idx_admin_invite_expires ON admin_invite(expires_at);
CREATE INDEX IF NOT EXISTS idx_admin_invite_created_by ON admin_invite(created_by);

-- Function to update updated_at timestamp for seasons
CREATE OR REPLACE FUNCTION update_season_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS update_season_updated_at_trigger ON season;
CREATE TRIGGER update_season_updated_at_trigger
    BEFORE UPDATE ON season
    FOR EACH ROW EXECUTE FUNCTION update_season_updated_at();

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Check if tables were created successfully
SELECT 
    table_name,
    CASE 
        WHEN table_name = 'season' THEN '🏆 Season management table'
        WHEN table_name = 'admin_invite' THEN '👥 Admin invite system table'
        ELSE table_name
    END as description
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('season', 'admin_invite')
ORDER BY table_name;

-- Show table structures
\d season;
\d admin_invite;

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================
-- ✅ Created season table for multi-season management
-- ✅ Created admin_invite table for committee admin registration  
-- ✅ Added proper constraints and indexes
-- ✅ Added triggers for automatic timestamp updates
-- ✅ NO existing data affected - completely safe migration
-- =============================================================================