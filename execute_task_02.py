#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - TASK 2 EXECUTOR
====================================
Safely executes Task 2: Add User Role System

This script:
✅ Adds role column to user table
✅ Creates role management functions
✅ Sets up permission structure
✅ Does NOT modify existing user data beyond adding default role
✅ Can be run multiple times safely
✅ Includes rollback functionality
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def execute_task_02():
    """Execute Task 2: Add User Role System"""
    conn = None
    cursor = None
    
    try:
        print("🚀 EXECUTING TASK 2: Add User Role System")
        print("=" * 70)
        
        # Connect to database
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if role column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user' 
              AND column_name = 'role'
        """)
        role_column_exists = cursor.fetchone() is not None
        
        if role_column_exists:
            print("⚠️  Role column already exists in user table")
            response = input("Continue with Task 2 anyway? (y/N): ").lower().strip()
            if response != 'y':
                print("❌ Task 2 cancelled by user")
                return False
        
        print("\n📋 Step 1: Adding role column to user table...")
        
        # Add role column if it doesn't exist
        if not role_column_exists:
            cursor.execute("""
                ALTER TABLE "user" 
                ADD COLUMN role VARCHAR(20) DEFAULT 'team_member' 
                CHECK (role IN ('team_member', 'committee_admin', 'super_admin'))
            """)
            print("   ✅ Role column added successfully")
            
            # Update existing users to have 'team_member' role (already default, but explicit)
            cursor.execute('UPDATE "user" SET role = \'team_member\' WHERE role IS NULL')
            updated_count = cursor.rowcount
            print(f"   ✅ Set role for {updated_count} existing users to 'team_member'")
        else:
            print("   ⏭️  Role column already exists, skipping")
        
        print("\n📋 Step 2: Creating role management functions...")
        
        # Create role management functions
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_user_role(user_id INTEGER)
            RETURNS VARCHAR(20) AS $$
            BEGIN
                RETURN (
                    SELECT role 
                    FROM "user" 
                    WHERE id = user_id
                );
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ get_user_role() function created")
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION is_super_admin(user_id INTEGER)
            RETURNS BOOLEAN AS $$
            BEGIN
                RETURN (
                    SELECT role = 'super_admin' 
                    FROM "user" 
                    WHERE id = user_id
                );
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ is_super_admin() function created")
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION is_committee_admin(user_id INTEGER)
            RETURNS BOOLEAN AS $$
            BEGIN
                RETURN (
                    SELECT role IN ('committee_admin', 'super_admin') 
                    FROM "user" 
                    WHERE id = user_id
                );
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ is_committee_admin() function created")
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION can_manage_season(user_id INTEGER)
            RETURNS BOOLEAN AS $$
            BEGIN
                RETURN (
                    SELECT role = 'super_admin' 
                    FROM "user" 
                    WHERE id = user_id
                );
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ can_manage_season() function created")
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION can_invite_admins(user_id INTEGER)
            RETURNS BOOLEAN AS $$
            BEGIN
                RETURN (
                    SELECT role IN ('committee_admin', 'super_admin') 
                    FROM "user" 
                    WHERE id = user_id
                );
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ can_invite_admins() function created")
        
        print("\n📋 Step 3: Creating role transition functions...")
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION promote_to_committee_admin(
                target_user_id INTEGER,
                promoting_user_id INTEGER
            )
            RETURNS BOOLEAN AS $$
            BEGIN
                -- Only super_admin can promote to committee_admin
                IF NOT is_super_admin(promoting_user_id) THEN
                    RAISE EXCEPTION 'Only super admin can promote users to committee admin';
                END IF;
                
                -- Check if target user exists
                IF NOT EXISTS (SELECT 1 FROM "user" WHERE id = target_user_id) THEN
                    RAISE EXCEPTION 'Target user does not exist';
                END IF;
                
                -- Update user role
                UPDATE "user" 
                SET role = 'committee_admin'
                WHERE id = target_user_id;
                
                RETURN TRUE;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ promote_to_committee_admin() function created")
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION demote_from_admin(
                target_user_id INTEGER,
                demoting_user_id INTEGER
            )
            RETURNS BOOLEAN AS $$
            BEGIN
                -- Only super_admin can demote admins
                IF NOT is_super_admin(demoting_user_id) THEN
                    RAISE EXCEPTION 'Only super admin can demote admin users';
                END IF;
                
                -- Cannot demote super_admin
                IF is_super_admin(target_user_id) THEN
                    RAISE EXCEPTION 'Cannot demote super admin';
                END IF;
                
                -- Check if target user exists
                IF NOT EXISTS (SELECT 1 FROM "user" WHERE id = target_user_id) THEN
                    RAISE EXCEPTION 'Target user does not exist';
                END IF;
                
                -- Update user role
                UPDATE "user" 
                SET role = 'team_member'
                WHERE id = target_user_id;
                
                RETURN TRUE;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ demote_from_admin() function created")
        
        print("\n📋 Step 4: Creating indexes...")
        
        # Create index on role column
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_role ON \"user\"(role)")
        print("   ✅ Index on user role created")
        
        print("\n📋 Step 5: Creating role statistics view...")
        
        cursor.execute("""
            CREATE OR REPLACE VIEW user_role_stats AS
            SELECT 
                role,
                COUNT(*) as user_count,
                CASE 
                    WHEN role = 'super_admin' THEN 'Full system access'
                    WHEN role = 'committee_admin' THEN 'Season management, limited invites'
                    WHEN role = 'team_member' THEN 'Team participation only'
                    ELSE 'Unknown role'
                END as description
            FROM "user"
            GROUP BY role
            ORDER BY 
                CASE role
                    WHEN 'super_admin' THEN 1
                    WHEN 'committee_admin' THEN 2
                    WHEN 'team_member' THEN 3
                    ELSE 4
                END;
        """)
        print("   ✅ user_role_stats view created")
        
        # Commit changes
        conn.commit()
        
        print("\n📋 Step 6: Verification...")
        
        # Verify role column exists
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                column_default,
                is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'user' 
              AND column_name = 'role'
        """)
        
        role_info = cursor.fetchone()
        if role_info:
            col_name, data_type, default_val, nullable = role_info
            print(f"   ✅ Role column: {col_name} ({data_type}, default: {default_val}, nullable: {nullable})")
        else:
            print("   ❌ Role column not found!")
            return False
        
        # Verify functions exist
        cursor.execute("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
              AND routine_name IN (
                  'get_user_role', 'is_super_admin', 'is_committee_admin',
                  'can_manage_season', 'can_invite_admins', 
                  'promote_to_committee_admin', 'demote_from_admin'
              )
            ORDER BY routine_name
        """)
        
        functions = [row[0] for row in cursor.fetchall()]
        expected_functions = [
            'can_invite_admins', 'can_manage_season', 'demote_from_admin',
            'get_user_role', 'is_committee_admin', 'is_super_admin',
            'promote_to_committee_admin'
        ]
        
        print(f"   📊 Functions created: {len(functions)}/{len(expected_functions)}")
        for func in functions:
            print(f"      ✅ {func}()")
        
        # Show current role distribution
        cursor.execute("SELECT * FROM user_role_stats")
        role_stats = cursor.fetchall()
        
        print("   📊 Current Role Distribution:")
        for role, count, description in role_stats:
            print(f"      {role}: {count} users - {description}")
        
        if len(functions) == len(expected_functions):
            print("\n🎉 TASK 2 COMPLETED SUCCESSFULLY!")
            print("✅ Added role system to user table")
            print("✅ Created role management functions")
            print("✅ Set up permission checking functions")
            print("✅ Added role transition functions with security")
            print("✅ Created role statistics view")
            print("✅ All existing users assigned 'team_member' role")
            
            return True
        else:
            print(f"\n❌ TASK 2 FAILED: Expected {len(expected_functions)} functions, found {len(functions)}")
            return False
            
    except Exception as e:
        print(f"\n💥 ERROR in Task 2: {e}")
        if conn:
            conn.rollback()
            print("🔄 Database changes rolled back")
        
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def rollback_task_02():
    """Rollback Task 2 changes if needed"""
    conn = None
    cursor = None
    
    try:
        print("\n🔄 ROLLBACK TASK 2: Remove User Role System")
        print("⚠️  WARNING: This will remove the role system from users!")
        
        response = input("Are you sure you want to rollback Task 2? (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Rollback cancelled")
            return False
        
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        # Drop functions
        functions_to_drop = [
            'get_user_role', 'is_super_admin', 'is_committee_admin',
            'can_manage_season', 'can_invite_admins', 
            'promote_to_committee_admin', 'demote_from_admin'
        ]
        
        for func in functions_to_drop:
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}(INTEGER) CASCADE")
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}(INTEGER, INTEGER) CASCADE")
        
        # Drop view
        cursor.execute("DROP VIEW IF EXISTS user_role_stats CASCADE")
        
        # Drop index
        cursor.execute("DROP INDEX IF EXISTS idx_user_role")
        
        # Remove role column
        cursor.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS role CASCADE')
        
        conn.commit()
        
        print("✅ Task 2 rollback completed")
        return True
        
    except Exception as e:
        print(f"💥 ERROR in Task 2 rollback: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        success = rollback_task_02()
    else:
        success = execute_task_02()
    
    sys.exit(0 if success else 1)