"""Test script to verify the stale bid fix works correctly."""

from models import Player, Bid
import unittest


class TestStaleBidFix(unittest.TestCase):
    """Test cases for the stale bid fix."""
    
    def setUp(self):
        """Set up test data."""
        # Create a mock player
        self.player = Player(id=1, name="Test Player", position="GK")
        
        # Mock bids - simulate old bid from round 1 and new bid from round 2
        self.old_bid = Bid(team_id=1, player_id=1, round_id=1, amount=1000)
        self.new_bid = Bid(team_id=1, player_id=1, round_id=2, amount=1500)
        
        # Add bids to player
        self.player.bids = [self.old_bid, self.new_bid]
    
    def test_has_bid_from_team_round_specific(self):
        """Test that has_bid_from_team works correctly with round ID."""
        team_id = 1
        
        # Should find bid in round 1
        self.assertTrue(self.player.has_bid_from_team(team_id, round_id=1))
        
        # Should find bid in round 2
        self.assertTrue(self.player.has_bid_from_team(team_id, round_id=2))
        
        # Should NOT find bid in round 3 (doesn't exist)
        self.assertFalse(self.player.has_bid_from_team(team_id, round_id=3))
        
        # Should NOT find bid from different team
        self.assertFalse(self.player.has_bid_from_team(team_id=2, round_id=1))
    
    def test_has_bid_from_team_all_rounds(self):
        """Test that has_bid_from_team still works without round ID (backward compatibility)."""
        team_id = 1
        
        # Should find any bid from team 1 across all rounds
        self.assertTrue(self.player.has_bid_from_team(team_id))
        
        # Should NOT find bid from different team
        self.assertFalse(self.player.has_bid_from_team(team_id=2))
    
    def test_stale_bid_scenario(self):
        """Test the specific stale bid scenario that was problematic."""
        team_id = 1
        
        # Player with only old bid from round 1 (lost/stale bid)
        stale_player = Player(id=2, name="Stale Player", position="GK")
        stale_bid = Bid(team_id=team_id, player_id=2, round_id=1, amount=500)  # Old round
        stale_player.bids = [stale_bid]
        
        # In new round 2, this player should NOT show as "already bidded"
        self.assertFalse(stale_player.has_bid_from_team(team_id, round_id=2))
        
        # But should show as "already bidded" for old round 1
        self.assertTrue(stale_player.has_bid_from_team(team_id, round_id=1))
        
        # And should show as "has any bid" without round specification
        self.assertTrue(stale_player.has_bid_from_team(team_id))


def run_tests():
    """Run the test cases."""
    print("=== TESTING STALE BID FIX ===")
    
    # Create test instance
    test = TestStaleBidFix()
    test.setUp()
    
    try:
        # Run each test
        test.test_has_bid_from_team_round_specific()
        print("✅ Round-specific bid detection: PASSED")
        
        test.test_has_bid_from_team_all_rounds()
        print("✅ All-rounds bid detection (backward compatibility): PASSED")
        
        test.test_stale_bid_scenario()
        print("✅ Stale bid scenario prevention: PASSED")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Stale bid issue is FIXED")
        print("✅ Teams will see clean interfaces in new rounds")
        print("✅ Bid history is preserved")
        
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"💥 ERROR RUNNING TESTS: {e}")
        return False
    
    return True


if __name__ == "__main__":
    run_tests()