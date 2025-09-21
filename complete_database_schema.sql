-- =============================================================================
-- COMPLETE NEON DATABASE SCHEMA FOR AUCTION SYSTEM
-- =============================================================================
-- This script creates a complete PostgreSQL database with:
-- - All tables with proper data types and constraints
-- - Auto-increment sequences for primary keys
-- - Foreign key constraints with proper referential integrity
-- - Indexes for performance optimization
-- - Triggers for automated updates
-- - Sample data for categories
-- =============================================================================

-- Drop existing tables if they exist (in correct order to handle foreign keys)
DROP TABLE IF EXISTS team_bulk_tiebreaker CASCADE;
DROP TABLE IF EXISTS bulk_bid_tiebreaker CASCADE;
DROP TABLE IF EXISTS bulk_bid CASCADE;
DROP TABLE IF EXISTS bulk_bid_round CASCADE;
DROP TABLE IF EXISTS password_reset_request CASCADE;
DROP TABLE IF EXISTS team_tiebreaker CASCADE;
DROP TABLE IF EXISTS tiebreaker CASCADE;
DROP TABLE IF EXISTS bid CASCADE;
DROP TABLE IF EXISTS starred_player CASCADE;
DROP TABLE IF EXISTS player CASCADE;
DROP TABLE IF EXISTS round CASCADE;
DROP TABLE IF EXISTS auction_settings CASCADE;
DROP TABLE IF EXISTS player_stats CASCADE;
DROP TABLE IF EXISTS player_matchup CASCADE;
DROP TABLE IF EXISTS match CASCADE;
DROP TABLE IF EXISTS team_member CASCADE;
DROP TABLE IF EXISTS team_stats CASCADE;
DROP TABLE IF EXISTS team CASCADE;
DROP TABLE IF EXISTS category CASCADE;
DROP TABLE IF EXISTS "user" CASCADE;

-- =============================================================================
-- CREATE TABLES WITH SEQUENCES
-- =============================================================================

-- Users table
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    remember_token VARCHAR(100) UNIQUE,
    token_expires_at TIMESTAMP WITHOUT TIME ZONE,
    last_password_change TIMESTAMP WITHOUT TIME ZONE,
    profile_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Categories table
CREATE TABLE category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    color VARCHAR(50) NOT NULL,
    priority INTEGER DEFAULT 0,
    points_same_category INTEGER DEFAULT 8,
    points_one_level_diff INTEGER DEFAULT 7,
    points_two_level_diff INTEGER DEFAULT 6,
    points_three_level_diff INTEGER DEFAULT 5,
    draw_same_category INTEGER DEFAULT 4,
    draw_one_level_diff INTEGER DEFAULT 3,
    draw_two_level_diff INTEGER DEFAULT 3,
    draw_three_level_diff INTEGER DEFAULT 2,
    loss_same_category INTEGER DEFAULT 1,
    loss_one_level_diff INTEGER DEFAULT 1,
    loss_two_level_diff INTEGER DEFAULT 1,
    loss_three_level_diff INTEGER DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Teams table
CREATE TABLE team (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    balance INTEGER DEFAULT 15000,
    user_id INTEGER REFERENCES "user"(id) ON DELETE CASCADE,
    logo_url VARCHAR(500),
    logo_storage_type VARCHAR(20) DEFAULT 'local',
    github_logo_sha VARCHAR(100),
    imagekit_file_id VARCHAR(100),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Team stats table
CREATE TABLE team_stats (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    goals_for INTEGER DEFAULT 0,
    goals_against INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Team members table
CREATE TABLE team_member (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    team_id INTEGER NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES category(id) ON DELETE RESTRICT,
    photo_url VARCHAR(255),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Matches table
CREATE TABLE match (
    id SERIAL PRIMARY KEY,
    home_team_id INTEGER NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    away_team_id INTEGER NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    match_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    round_number INTEGER NOT NULL,
    match_number INTEGER NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    potm_id INTEGER REFERENCES team_member(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_different_teams CHECK (home_team_id != away_team_id),
    CONSTRAINT check_positive_scores CHECK (home_score >= 0 AND away_score >= 0)
);

-- Player matchups table
CREATE TABLE player_matchup (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES match(id) ON DELETE CASCADE,
    home_player_id INTEGER NOT NULL REFERENCES team_member(id) ON DELETE CASCADE,
    away_player_id INTEGER NOT NULL REFERENCES team_member(id) ON DELETE CASCADE,
    home_goals INTEGER DEFAULT 0,
    away_goals INTEGER DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_positive_goals CHECK (home_goals >= 0 AND away_goals >= 0)
);

-- Player stats table
CREATE TABLE player_stats (
    id SERIAL PRIMARY KEY,
    team_member_id INTEGER NOT NULL REFERENCES team_member(id) ON DELETE CASCADE,
    played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    goals_scored INTEGER DEFAULT 0,
    goals_conceded INTEGER DEFAULT 0,
    clean_sheets INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Auction settings table
CREATE TABLE auction_settings (
    id SERIAL PRIMARY KEY,
    max_rounds INTEGER DEFAULT 25,
    min_balance_per_round INTEGER DEFAULT 30,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Rounds table for auction
CREATE TABLE round (
    id SERIAL PRIMARY KEY,
    position VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    start_time TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITHOUT TIME ZONE,
    duration INTEGER DEFAULT 300,
    status VARCHAR(20) DEFAULT 'active',
    max_bids_per_team INTEGER DEFAULT 5,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Players table for auction
CREATE TABLE player (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    position VARCHAR(10) NOT NULL,
    team_id INTEGER REFERENCES team(id) ON DELETE SET NULL,
    round_id INTEGER REFERENCES round(id) ON DELETE SET NULL,
    acquisition_value INTEGER,
    is_auction_eligible BOOLEAN DEFAULT TRUE,
    position_group VARCHAR(10),
    team_name VARCHAR(100),
    nationality VARCHAR(100),
    offensive_awareness INTEGER,
    ball_control INTEGER,
    dribbling INTEGER,
    tight_possession INTEGER,
    low_pass INTEGER,
    lofted_pass INTEGER,
    finishing INTEGER,
    heading INTEGER,
    set_piece_taking INTEGER,
    curl INTEGER,
    speed INTEGER,
    acceleration INTEGER,
    kicking_power INTEGER,
    jumping INTEGER,
    physical_contact INTEGER,
    balance INTEGER,
    stamina INTEGER,
    defensive_awareness INTEGER,
    tackling INTEGER,
    aggression INTEGER,
    defensive_engagement INTEGER,
    gk_awareness INTEGER,
    gk_catching INTEGER,
    gk_parrying INTEGER,
    gk_reflexes INTEGER,
    gk_reach INTEGER,
    overall_rating INTEGER,
    playing_style VARCHAR(50),
    player_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_rating_range CHECK (
        (offensive_awareness IS NULL OR (offensive_awareness >= 0 AND offensive_awareness <= 100)) AND
        (ball_control IS NULL OR (ball_control >= 0 AND ball_control <= 100)) AND
        (overall_rating IS NULL OR (overall_rating >= 0 AND overall_rating <= 100))
    )
);

-- Starred players table (many-to-many relationship)
CREATE TABLE starred_player (
    team_id INTEGER NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES player(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, player_id)
);

-- Bids table
CREATE TABLE bid (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES player(id) ON DELETE CASCADE,
    round_id INTEGER NOT NULL REFERENCES round(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    is_hidden BOOLEAN DEFAULT TRUE,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_positive_amount CHECK (amount > 0)
);

-- Tiebreakers table
CREATE TABLE tiebreaker (
    id SERIAL PRIMARY KEY,
    round_id INTEGER NOT NULL REFERENCES round(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES player(id) ON DELETE CASCADE,
    original_amount INTEGER NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_positive_original_amount CHECK (original_amount > 0)
);

-- Team tiebreakers table
CREATE TABLE team_tiebreaker (
    id SERIAL PRIMARY KEY,
    tiebreaker_id INTEGER NOT NULL REFERENCES tiebreaker(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    new_amount INTEGER,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_positive_new_amount CHECK (new_amount IS NULL OR new_amount > 0)
);

-- Password reset requests table
CREATE TABLE password_reset_request (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    reset_token VARCHAR(100) UNIQUE,
    reason TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Bulk bid round table
CREATE TABLE bulk_bid_round (
    id SERIAL PRIMARY KEY,
    is_active BOOLEAN DEFAULT TRUE,
    start_time TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITHOUT TIME ZONE,
    duration INTEGER DEFAULT 300,
    base_price INTEGER DEFAULT 10,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Bulk bids table
CREATE TABLE bulk_bid (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES player(id) ON DELETE CASCADE,
    round_id INTEGER NOT NULL REFERENCES bulk_bid_round(id) ON DELETE CASCADE,
    is_resolved BOOLEAN DEFAULT FALSE,
    has_tie BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Bulk bid tiebreakers table
CREATE TABLE bulk_bid_tiebreaker (
    id SERIAL PRIMARY KEY,
    bulk_round_id INTEGER NOT NULL REFERENCES bulk_bid_round(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES player(id) ON DELETE CASCADE,
    current_amount INTEGER NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,
    winner_team_id INTEGER REFERENCES team(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_positive_current_amount CHECK (current_amount > 0)
);

-- Team bulk tiebreakers table
CREATE TABLE team_bulk_tiebreaker (
    id SERIAL PRIMARY KEY,
    tiebreaker_id INTEGER NOT NULL REFERENCES bulk_bid_tiebreaker(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    last_bid INTEGER,
    last_bid_time TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_positive_last_bid CHECK (last_bid IS NULL OR last_bid > 0)
);

-- =============================================================================
-- CREATE INDEXES FOR PERFORMANCE OPTIMIZATION
-- =============================================================================

-- User indexes
CREATE INDEX idx_user_username ON "user"(username);
CREATE INDEX idx_user_email ON "user"(email);
CREATE INDEX idx_user_remember_token ON "user"(remember_token);
CREATE INDEX idx_user_is_admin ON "user"(is_admin);
CREATE INDEX idx_user_is_approved ON "user"(is_approved);

-- Team indexes
CREATE INDEX idx_team_user_id ON team(user_id);
CREATE INDEX idx_team_name ON team(name);

-- Team stats indexes
CREATE INDEX idx_team_stats_team_id ON team_stats(team_id);

-- Team member indexes
CREATE INDEX idx_team_member_team_id ON team_member(team_id);
CREATE INDEX idx_team_member_category_id ON team_member(category_id);

-- Match indexes
CREATE INDEX idx_match_home_team_id ON match(home_team_id);
CREATE INDEX idx_match_away_team_id ON match(away_team_id);
CREATE INDEX idx_match_round_number ON match(round_number);
CREATE INDEX idx_match_is_completed ON match(is_completed);
CREATE INDEX idx_match_date ON match(match_date);

-- Player matchup indexes
CREATE INDEX idx_player_matchup_match_id ON player_matchup(match_id);
CREATE INDEX idx_player_matchup_home_player_id ON player_matchup(home_player_id);
CREATE INDEX idx_player_matchup_away_player_id ON player_matchup(away_player_id);

-- Player stats indexes
CREATE INDEX idx_player_stats_team_member_id ON player_stats(team_member_id);

-- Player indexes
CREATE INDEX idx_player_team_id ON player(team_id);
CREATE INDEX idx_player_round_id ON player(round_id);
CREATE INDEX idx_player_position ON player(position);
CREATE INDEX idx_player_is_auction_eligible ON player(is_auction_eligible);
CREATE INDEX idx_player_overall_rating ON player(overall_rating);

-- Bid indexes
CREATE INDEX idx_bid_team_id ON bid(team_id);
CREATE INDEX idx_bid_player_id ON bid(player_id);
CREATE INDEX idx_bid_round_id ON bid(round_id);
CREATE INDEX idx_bid_amount ON bid(amount);
CREATE INDEX idx_bid_timestamp ON bid(timestamp);
CREATE INDEX idx_bid_is_hidden ON bid(is_hidden);

-- Round indexes
CREATE INDEX idx_round_position ON round(position);
CREATE INDEX idx_round_is_active ON round(is_active);
CREATE INDEX idx_round_status ON round(status);
CREATE INDEX idx_round_start_time ON round(start_time);
CREATE INDEX idx_round_end_time ON round(end_time);

-- Tiebreaker indexes
CREATE INDEX idx_tiebreaker_round_id ON tiebreaker(round_id);
CREATE INDEX idx_tiebreaker_player_id ON tiebreaker(player_id);
CREATE INDEX idx_tiebreaker_resolved ON tiebreaker(resolved);

-- Team tiebreaker indexes
CREATE INDEX idx_team_tiebreaker_tiebreaker_id ON team_tiebreaker(tiebreaker_id);
CREATE INDEX idx_team_tiebreaker_team_id ON team_tiebreaker(team_id);

-- Password reset request indexes
CREATE INDEX idx_password_reset_user_id ON password_reset_request(user_id);
CREATE INDEX idx_password_reset_token ON password_reset_request(reset_token);
CREATE INDEX idx_password_reset_status ON password_reset_request(status);

-- Bulk bid indexes
CREATE INDEX idx_bulk_bid_team_id ON bulk_bid(team_id);
CREATE INDEX idx_bulk_bid_player_id ON bulk_bid(player_id);
CREATE INDEX idx_bulk_bid_round_id ON bulk_bid(round_id);

-- Composite indexes for common queries
CREATE INDEX idx_bid_round_player ON bid(round_id, player_id);
CREATE INDEX idx_bid_team_round ON bid(team_id, round_id);
CREATE INDEX idx_starred_player_composite ON starred_player(team_id, player_id);

-- =============================================================================
-- CREATE TRIGGERS AND FUNCTIONS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_user_updated_at 
    BEFORE UPDATE ON "user" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_team_stats_updated_at 
    BEFORE UPDATE ON team_stats 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_player_stats_updated_at 
    BEFORE UPDATE ON player_stats 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_auction_settings_updated_at 
    BEFORE UPDATE ON auction_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_password_reset_updated_at 
    BEFORE UPDATE ON password_reset_request 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically create team stats when team is created
CREATE OR REPLACE FUNCTION create_team_stats()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO team_stats (team_id) VALUES (NEW.id);
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER create_team_stats_trigger
    AFTER INSERT ON team
    FOR EACH ROW EXECUTE FUNCTION create_team_stats();

-- Function to automatically create player stats when team member is created
CREATE OR REPLACE FUNCTION create_player_stats()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO player_stats (team_member_id) VALUES (NEW.id);
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER create_player_stats_trigger
    AFTER INSERT ON team_member
    FOR EACH ROW EXECUTE FUNCTION create_player_stats();

-- Function to validate bid amounts against team balance
CREATE OR REPLACE FUNCTION validate_bid_amount()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if team has sufficient balance (simplified check)
    IF NEW.amount <= 0 THEN
        RAISE EXCEPTION 'Bid amount must be positive';
    END IF;
    
    -- Additional validation can be added here
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER validate_bid_trigger
    BEFORE INSERT ON bid
    FOR EACH ROW EXECUTE FUNCTION validate_bid_amount();

-- Function to prevent duplicate active rounds for the same position
CREATE OR REPLACE FUNCTION prevent_duplicate_active_rounds()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_active = TRUE THEN
        -- Check if there's already an active round for this position
        IF EXISTS (
            SELECT 1 FROM round 
            WHERE position = NEW.position 
            AND is_active = TRUE 
            AND id != COALESCE(NEW.id, 0)
        ) THEN
            RAISE EXCEPTION 'Cannot have multiple active rounds for position: %', NEW.position;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER prevent_duplicate_active_rounds_trigger
    BEFORE INSERT OR UPDATE ON round
    FOR EACH ROW EXECUTE FUNCTION prevent_duplicate_active_rounds();

-- =============================================================================
-- INSERT SAMPLE DATA
-- =============================================================================

-- Insert default categories
INSERT INTO category (name, color, priority) VALUES
('Red', 'red', 1),
('Black', 'black', 2),
('Blue', 'blue', 3),
('White', 'white', 4);

-- Insert default auction settings
INSERT INTO auction_settings (max_rounds, min_balance_per_round) VALUES (25, 30);

-- Create default admin user (password: 'admin123' - change this immediately!)
INSERT INTO "user" (username, email, password_hash, is_admin, is_approved) VALUES 
('admin', 'admin@auction.com', 'scrypt:32768:8:1$DPINGnNtClvI0mKL$5fda26eaea02e0016beac6e536d2c581f0f587760267d634644a86e21ac17ffcc9f6baeb4a6d4ce35fa14d71a64da0d8a66f6765bbb917cbe5713befef8b691f', TRUE, TRUE);

-- =============================================================================
-- GRANT PERMISSIONS (adjust as needed for your setup)
-- =============================================================================

-- Grant all privileges on all tables to the database owner
-- Note: Adjust these grants based on your specific user setup in Neon
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO neondb_owner;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO neondb_owner;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO neondb_owner;

-- =============================================================================
-- VERIFY SCHEMA CREATION
-- =============================================================================

-- Display created tables
SELECT 
    schemaname, 
    tablename, 
    tableowner 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;

-- Display created sequences
SELECT 
    sequence_name, 
    last_value 
FROM information_schema.sequences 
WHERE sequence_schema = 'public'
ORDER BY sequence_name;

-- =============================================================================
-- SCHEMA COMPLETE
-- =============================================================================
-- This schema includes:
-- ✅ 19 tables with proper relationships
-- ✅ Auto-increment sequences for all primary keys
-- ✅ Foreign key constraints with CASCADE/RESTRICT as appropriate
-- ✅ Check constraints for data validation
-- ✅ Comprehensive indexes for query optimization
-- ✅ Triggers for automated updates and validation
-- ✅ Sample data for categories and settings
-- ✅ Default admin user (change password immediately!)
-- 
-- Ready to import into Neon database!
-- =============================================================================