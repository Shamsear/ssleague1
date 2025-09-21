# Database Setup Information

## 📁 Files Created
- `complete_database_schema.sql` - Complete PostgreSQL schema with all tables, indexes, triggers, and sample data

## 🔐 Default Admin Credentials
After running the SQL script, you can login with:

**Username:** `admin`  
**Email:** `admin@auction.com`  
**Password:** `admin123`

> ⚠️ **IMPORTANT:** Change this password immediately after first login!

## 🚀 How to Use

1. **Create a new database in Neon:**
   - Go to your Neon console
   - Create a new database (or use an existing one)
   - Copy the connection string

2. **Import the schema:**
   - Download the `complete_database_schema.sql` file
   - In Neon console, go to SQL Editor
   - Copy and paste the entire content of the SQL file
   - Run the script

3. **Verify the setup:**
   - Check that all 19 tables were created
   - Verify sequences are working
   - Test login with the admin credentials

## 📊 What's Included

### Tables Created (19 total):
- `user` - User accounts and authentication
- `team` - Team information and logos
- `team_stats` - Team statistics 
- `team_member` - Individual team members
- `category` - Player categories (Red, Black, Blue, White)
- `match` - Match results and information
- `player_matchup` - Individual player matchups in matches
- `player_stats` - Individual player statistics
- `player` - Players available for auction
- `starred_player` - Players starred by teams
- `round` - Auction rounds
- `bid` - Individual bids in auctions
- `tiebreaker` - Tiebreaker situations
- `team_tiebreaker` - Team participation in tiebreakers
- `bulk_bid_round` - Bulk bidding rounds
- `bulk_bid` - Bulk bids
- `bulk_bid_tiebreaker` - Bulk bid tiebreakers
- `team_bulk_tiebreaker` - Team participation in bulk tiebreakers
- `auction_settings` - Global auction settings
- `password_reset_request` - Password reset requests

### Features Included:
✅ Auto-increment primary keys with sequences  
✅ Foreign key constraints with proper CASCADE/RESTRICT  
✅ Check constraints for data validation  
✅ Comprehensive indexes for performance  
✅ Triggers for automated updates  
✅ Sample data (categories, settings, admin user)  
✅ Password hashing support  
✅ Timestamp tracking  

### Default Categories:
- Red (Priority 1)
- Black (Priority 2) 
- Blue (Priority 3)
- White (Priority 4)

### Default Settings:
- Max rounds: 25
- Min balance per round: 30

## 🔧 Post-Setup Steps

1. **Change admin password** via the web interface
2. **Update email address** for the admin account
3. **Create additional admin users** if needed
4. **Configure team logos** and other assets
5. **Import player data** if you have existing data

## 🐛 Troubleshooting

If you encounter issues:

1. **Permission errors:** Make sure the database user has sufficient privileges
2. **Sequence errors:** The script includes proper sequence setup for auto-increment
3. **Foreign key errors:** Import the script as-is - tables are created in the correct order
4. **Login issues:** Use exactly `admin` / `admin123` (case-sensitive)

## 💡 Notes

- All timestamps are in UTC
- Password hashing uses Werkzeug's scrypt method
- The schema supports both individual and bulk bidding
- Team stats and player stats are automatically created via triggers
- The database includes comprehensive audit trails with timestamps