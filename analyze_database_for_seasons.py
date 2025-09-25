import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def analyze_database_structure():
    """Analyze the current database structure for season implementation planning"""
    conn = psycopg2.connect(NEON_DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("=== CURRENT DATABASE ANALYSIS FOR MULTI-SEASON SYSTEM ===")
        
        # 1. Get all tables in the database
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        print(f"\n📊 Current Tables ({len(tables)} total):")
        for table in tables:
            print(f"   - {table[0]}")
        
        # 2. Check current user roles/admin structure
        cursor.execute("""
            SELECT 
                id, username, email, is_admin, is_approved, created_at
            FROM "user" 
            ORDER BY is_admin DESC, created_at ASC
        """)
        users = cursor.fetchall()
        
        print(f"\n👥 Current Users ({len(users)} total):")
        admin_count = 0
        user_count = 0
        
        for user in users:
            user_id, username, email, is_admin, is_approved, created_at = user
            status = "ADMIN" if is_admin else "USER"
            approval = "✅" if is_approved else "❌"
            if is_admin:
                admin_count += 1
            else:
                user_count += 1
            print(f"   {status}: {username} ({email}) {approval} - Created: {created_at.strftime('%Y-%m-%d')}")
        
        print(f"\n   Summary: {admin_count} admins, {user_count} regular users")
        
        # 3. Check current data volumes
        data_tables = ['team', 'player', 'round', 'bid', 'match', 'team_member']
        
        print(f"\n📈 Current Data Volumes:")
        for table_name in data_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"   {table_name}: {count} records")
            except Exception as e:
                print(f"   {table_name}: Table not found or error ({e})")
        
        # 4. Check if season-related columns already exist
        print(f"\n🔍 Checking for existing season-related columns:")
        season_check_tables = ['team', 'player', 'round', 'bid']
        
        for table_name in season_check_tables:
            try:
                cursor.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    AND table_schema = 'public'
                    ORDER BY column_name
                """)
                columns = cursor.fetchall()
                column_names = [col[0] for col in columns]
                
                # Check if season_id exists
                has_season_id = 'season_id' in column_names
                season_status = "✅ HAS season_id" if has_season_id else "❌ NO season_id"
                print(f"   {table_name}: {season_status}")
                
                if 'created_at' not in column_names:
                    print(f"      ⚠️  Missing created_at timestamp")
                    
            except Exception as e:
                print(f"   {table_name}: Error checking ({e})")
        
        # 5. Check current active rounds/seasons pattern
        cursor.execute("""
            SELECT COUNT(*) as total_rounds,
                   COUNT(CASE WHEN is_active = true THEN 1 END) as active_rounds,
                   MIN(created_at) as first_round,
                   MAX(created_at) as latest_round
            FROM round
        """)
        round_stats = cursor.fetchone()
        
        if round_stats and round_stats[0] > 0:
            total, active, first, latest = round_stats
            print(f"\n🎯 Round Activity Analysis:")
            print(f"   Total rounds: {total}")
            print(f"   Active rounds: {active}")
            print(f"   First round: {first.strftime('%Y-%m-%d %H:%M') if first else 'N/A'}")
            print(f"   Latest round: {latest.strftime('%Y-%m-%d %H:%M') if latest else 'N/A'}")
            
            if first and latest:
                duration = latest - first
                print(f"   Activity span: {duration.days} days")
        
        # 6. Check user table structure for role expansion
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'user' 
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        user_columns = cursor.fetchall()
        
        print(f"\n👤 User Table Structure:")
        has_user_role = False
        for col in user_columns:
            col_name, data_type, nullable, default = col
            if col_name == 'user_role':
                has_user_role = True
            print(f"   {col_name}: {data_type} {'NULL' if nullable == 'YES' else 'NOT NULL'}")
        
        role_status = "✅ HAS user_role" if has_user_role else "❌ NEEDS user_role column"
        print(f"\n   Role system: {role_status}")
        
        # 7. Summary and recommendations
        print(f"\n" + "="*60)
        print("📋 SEASON IMPLEMENTATION READINESS ASSESSMENT")
        print("="*60)
        
        print(f"\n✅ EXISTING ASSETS:")
        print(f"   • {admin_count} existing admin(s) (can become committee admins)")
        print(f"   • Rich data structure with {len(tables)} tables")
        print(f"   • Active auction system with {round_stats[0] if round_stats else 0} rounds")
        print(f"   • User management system in place")
        
        print(f"\n🔧 REQUIRED CHANGES:")
        print(f"   • Add 'season' table")
        print(f"   • Add 'admin_invite' table") 
        print(f"   • Add season_id columns to data tables")
        print(f"   • Add user_role column (super_admin, admin, user)")
        print(f"   • Create migration script for existing data")
        
        print(f"\n💡 MIGRATION STRATEGY:")
        print(f"   1. Create new season tables")
        print(f"   2. Add Season 1 as default season")
        print(f"   3. Link all existing data to Season 1")
        print(f"   4. Upgrade one existing admin to super_admin")
        print(f"   5. Implement season-aware queries")
        
        # 8. Check for any foreign key constraints that might affect migration
        cursor.execute("""
            SELECT 
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
            ORDER BY tc.table_name, tc.constraint_name
        """)
        
        fk_constraints = cursor.fetchall()
        
        if fk_constraints:
            print(f"\n🔗 Foreign Key Constraints ({len(fk_constraints)} total):")
            current_table = None
            for fk in fk_constraints[:10]:  # Show first 10
                constraint, table, column, ref_table, ref_column = fk
                if table != current_table:
                    print(f"   {table}:")
                    current_table = table
                print(f"     {column} -> {ref_table}.{ref_column}")
            
            if len(fk_constraints) > 10:
                print(f"     ... and {len(fk_constraints) - 10} more")
        
        print(f"\n🎯 NEXT STEPS:")
        print(f"   1. Review current data and confirm migration approach")
        print(f"   2. Create season management system")
        print(f"   3. Implement multi-admin hierarchy")
        print(f"   4. Add season-aware filtering to all queries")
        print(f"   5. Create super admin interface")
        
    except Exception as e:
        print(f"❌ Error analyzing database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    analyze_database_structure()