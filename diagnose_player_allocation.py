#!/usr/bin/env python3
"""
Diagnostic script to check why players are not getting assigned in rounds
"""

from app import app, db
from models import Round, Bid, Team, Player, Tiebreaker, TeamTiebreaker
from sqlalchemy import func

def diagnose_player_allocation():
    with app.app_context():
        print("🔍 Player Allocation Diagnostic Report")
        print("=" * 60)
        
        # Get recent rounds
        recent_rounds = Round.query.filter_by(is_active=False).order_by(Round.id.desc()).limit(5).all()
        
        if not recent_rounds:
            print("❌ No completed rounds found")
            return
            
        for round_obj in recent_rounds:
            print(f"\n📊 ROUND #{round_obj.id} ({round_obj.position}) - Status: {round_obj.status}")
            print("-" * 40)
            
            # Get all bids for this round
            all_bids = Bid.query.filter_by(round_id=round_obj.id).all()
            print(f"Total bids placed: {len(all_bids)}")
            
            if not all_bids:
                print("   ⚠️  No bids placed in this round")
                continue
                
            # Count bids per team
            team_bid_counts = {}
            for bid in all_bids:
                team_bid_counts[bid.team_id] = team_bid_counts.get(bid.team_id, 0) + 1
            
            print(f"Required bids per team: {round_obj.max_bids_per_team}")
            print("Bid counts per team:")
            
            valid_teams = []
            invalid_teams = []
            
            for team_id, count in team_bid_counts.items():
                team = Team.query.get(team_id)
                team_name = team.name if team else f"Team {team_id}"
                status = "✅ VALID" if count == round_obj.max_bids_per_team else "❌ INVALID"
                print(f"   {team_name}: {count} bids - {status}")
                
                if count == round_obj.max_bids_per_team:
                    valid_teams.append(team_id)
                else:
                    invalid_teams.append(team_id)
            
            print(f"\nValid teams (exact bid count): {len(valid_teams)}")
            print(f"Invalid teams (wrong bid count): {len(invalid_teams)}")
            
            # Check valid bids only
            valid_bids = [bid for bid in all_bids if bid.team_id in valid_teams]
            print(f"Valid bids being processed: {len(valid_bids)}")
            
            if not valid_bids:
                print("   ⚠️  NO VALID BIDS - This is why no players were assigned!")
                print("   💡 Teams must place exactly the required number of bids")
                continue
            
            # Show bid details
            print("\nValid bids breakdown:")
            for bid in sorted(valid_bids, key=lambda x: x.amount, reverse=True):
                team = Team.query.get(bid.team_id)
                player = Player.query.get(bid.player_id)
                team_name = team.name if team else f"Team {bid.team_id}"
                player_name = player.name if player else f"Player {bid.player_id}"
                print(f"   {team_name}: £{bid.amount:,} for {player_name}")
            
            # Check for player assignments
            assigned_players = Player.query.filter(
                Player.team_id.isnot(None),
                Player.id.in_([bid.player_id for bid in valid_bids])
            ).all()
            
            print(f"\nPlayers actually assigned: {len(assigned_players)}")
            for player in assigned_players:
                team = Team.query.get(player.team_id)
                team_name = team.name if team else f"Team {player.team_id}"
                print(f"   {player.name} → {team_name} (£{player.acquisition_value:,})")
            
            # Check for tiebreakers
            tiebreakers = Tiebreaker.query.filter_by(round_id=round_obj.id).all()
            if tiebreakers:
                print(f"\nTiebreakers created: {len(tiebreakers)}")
                for tb in tiebreakers:
                    player = Player.query.get(tb.player_id)
                    player_name = player.name if player else f"Player {tb.player_id}"
                    print(f"   {player_name}: £{tb.original_amount:,} - Resolved: {tb.resolved}")
            
            # Analyze why no assignments if that's the case
            if len(assigned_players) == 0 and valid_bids:
                print("\n🚨 ISSUE ANALYSIS:")
                print("   Valid bids exist but no players were assigned!")
                
                # Check if it's because of multiple teams bidding same amounts
                bid_amounts = [bid.amount for bid in valid_bids]
                unique_amounts = set(bid_amounts)
                if len(unique_amounts) < len(bid_amounts):
                    print("   💡 Possible cause: Multiple teams with same bid amounts")
                    
                # Group bids by player
                player_bids = {}
                for bid in valid_bids:
                    if bid.player_id not in player_bids:
                        player_bids[bid.player_id] = []
                    player_bids[bid.player_id].append(bid)
                
                print(f"   Players with bids: {len(player_bids)}")
                for player_id, bids in player_bids.items():
                    player = Player.query.get(player_id)
                    player_name = player.name if player else f"Player {player_id}"
                    if len(bids) > 1:
                        amounts = [f"£{b.amount:,}" for b in bids]
                        print(f"   🔥 {player_name}: {len(bids)} bids ({', '.join(amounts)}) - COMPETITION!")
                    else:
                        print(f"   📝 {player_name}: 1 bid (£{bids[0].amount:,})")
        
        print(f"\n" + "=" * 60)
        print("🎯 SUMMARY & RECOMMENDATIONS:")
        print("1. Teams must place EXACTLY the required number of bids")
        print("2. Only bids from teams with correct bid counts are processed")
        print("3. If multiple teams bid the same amount for same player, tiebreaker is created")
        print("4. Check tiebreaker resolution if players are stuck in 'processing' state")

if __name__ == "__main__":
    diagnose_player_allocation()