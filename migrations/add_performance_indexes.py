"""Add performance indexes for round operations

Revision ID: performance_indexes
Revises: 
Create Date: 2025-09-23 09:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'performance_indexes'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Add critical performance indexes for round operations"""
    
    # Critical indexes for round operations
    try:
        op.create_index('idx_round_is_active', 'round', ['is_active'])
        print("✅ Created index: idx_round_is_active")
    except Exception as e:
        print(f"⚠️ Index idx_round_is_active may already exist: {e}")
    
    try:
        op.create_index('idx_user_is_approved', 'user', ['is_approved'])
        print("✅ Created index: idx_user_is_approved")
    except Exception as e:
        print(f"⚠️ Index idx_user_is_approved may already exist: {e}")
    
    # Composite indexes for player queries - most critical for performance
    try:
        op.create_index('idx_player_position_team_eligible', 'player', 
                       ['position', 'team_id', 'is_auction_eligible'])
        print("✅ Created composite index: idx_player_position_team_eligible")
    except Exception as e:
        print(f"⚠️ Index idx_player_position_team_eligible may already exist: {e}")
    
    try:
        op.create_index('idx_player_position_group_team_eligible', 'player', 
                       ['position_group', 'team_id', 'is_auction_eligible'])
        print("✅ Created composite index: idx_player_position_group_team_eligible")
    except Exception as e:
        print(f"⚠️ Index idx_player_position_group_team_eligible may already exist: {e}")
    
    # Additional helpful indexes
    try:
        op.create_index('idx_player_team_id', 'player', ['team_id'])
        print("✅ Created index: idx_player_team_id")
    except Exception as e:
        print(f"⚠️ Index idx_player_team_id may already exist: {e}")
    
    try:
        op.create_index('idx_player_round_id', 'player', ['round_id'])
        print("✅ Created index: idx_player_round_id")
    except Exception as e:
        print(f"⚠️ Index idx_player_round_id may already exist: {e}")
    
    try:
        op.create_index('idx_bid_round_id', 'bid', ['round_id'])
        print("✅ Created index: idx_bid_round_id")
    except Exception as e:
        print(f"⚠️ Index idx_bid_round_id may already exist: {e}")
    
    try:
        op.create_index('idx_bid_team_round', 'bid', ['team_id', 'round_id'])
        print("✅ Created composite index: idx_bid_team_round")
    except Exception as e:
        print(f"⚠️ Index idx_bid_team_round may already exist: {e}")

def downgrade():
    """Remove the performance indexes"""
    
    # Drop indexes in reverse order
    try:
        op.drop_index('idx_bid_team_round', table_name='bid')
        op.drop_index('idx_bid_round_id', table_name='bid')
        op.drop_index('idx_player_round_id', table_name='player')
        op.drop_index('idx_player_team_id', table_name='player')
        op.drop_index('idx_player_position_group_team_eligible', table_name='player')
        op.drop_index('idx_player_position_team_eligible', table_name='player')
        op.drop_index('idx_user_is_approved', table_name='user')
        op.drop_index('idx_round_is_active', table_name='round')
        print("✅ All performance indexes dropped")
    except Exception as e:
        print(f"⚠️ Some indexes may not exist during downgrade: {e}")