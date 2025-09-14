# Budget Planner Priority System Documentation

## Overview
The Budget Planner includes an intelligent priority system that helps users make strategic decisions about which positions to prioritize during auctions. The system categorizes positions based on their importance for team composition and displays visual indicators to guide bidding strategies.

## Position Priority Levels

### High Priority (RED indicators)
**When shown:** When critical positions lack sufficient players
**Visual:** Red background with warning icon and "HIGH PRIORITY" text
**Positions affected:**
- **GK (Goalkeeper):** Shows high priority when you have 0 goalkeepers
- **CB (Center Back):** Shows high priority when you have fewer than 2 center backs  
- **CF (Center Forward):** Shows high priority when you have fewer than 2 center forwards

**Why these are high priority:**
- GK: Essential - every team needs at least one goalkeeper
- CB: Core defense - you need at least 2 center backs for a solid defensive line
- CF: Main attack - you need at least 2 center forwards for attacking options

### Medium Priority (ORANGE indicators)
**When shown:** When important supporting positions need players
**Visual:** Orange background with info icon and "MEDIUM PRIORITY" text
**Positions affected:**
- **RB/LB (Fullbacks):** When you have 0 right/left backs
- **DMF/CMF/AMF (Midfield):** When you have 0 in any core midfield position
- **LMF/RMF/LWF/RWF/SS (Wing/Support):** When you have 0 in wing or support positions

**Why these are medium priority:**
- Fullbacks provide width and defensive stability
- Core midfielders control the game's tempo and flow
- Wing players offer attacking width and creative options

### Depth Options (YELLOW indicators) 
**When shown:** When you already have minimum requirements but could benefit from squad depth
**Visual:** Yellow background with info icon and "DEPTH OPTION" text
**Positions affected:**
- **CB/CF:** When you have 2 players but fewer than 3 (adding depth)
- **RB/LB/DMF/CMF:** When you have 1 player but fewer than 2 (backup options)

**Why depth is valuable:**
- Provides rotation options during long seasons
- Insurance against injuries or suspensions
- Tactical flexibility with different playing styles

## Budget Calculation Logic

### Safe Spending Amount
The system calculates how much you can safely spend while maintaining minimum balance requirements:
```
Safe Spending = Current Balance - (Min Balance Per Round × Remaining Rounds)
```

### Position-Specific Budget Recommendations
Based on market averages and priority levels:
- **High Priority positions:** Higher suggested budgets (60-80% of position average)
- **Medium Priority positions:** Moderate suggested budgets (50-60% of position average)  
- **Depth Options:** Conservative suggested budgets (35-40% of position average)

## Strategic Implications

### Early Auction Rounds
- Focus budget on HIGH PRIORITY positions first
- Ensure you secure essential roles (GK, CB, CF) early
- Don't overspend on depth when core positions are empty

### Mid-Stage Auctions
- Address MEDIUM PRIORITY positions
- Build a balanced squad across all areas
- Consider position versatility and playing styles

### Late Auction Rounds
- Add DEPTH OPTIONS if budget allows
- Look for value picks and bargains
- Ensure compliance with minimum balance requirements

## How RB Gets High Priority

**RB (Right Back) shows as HIGH PRIORITY when:**
1. Your team has 0 Right Backs AND
2. The system categorizes RB among essential defensive positions

The system recognizes that:
- Modern football requires attacking fullbacks
- You need at least one player per flank for tactical flexibility
- RB provides crucial width in both defense and attack
- Without fullbacks, your formation options become very limited

## Visual Indicators Guide

| Priority Level | Background | Icon | Text Style |
|---------------|------------|------|------------|
| High Priority | Red (`bg-red-100`) | ⚠️ Warning | Bold, uppercase |
| Medium Priority | Orange (`bg-orange-100`) | ℹ️ Info | Bold, uppercase |
| Depth Option | Yellow (`bg-yellow-100`) | ℹ️ Info | Bold, uppercase |

## Tips for Using the Priority System

1. **Trust the indicators:** They're based on solid tactical principles
2. **Budget accordingly:** Allocate more funds to high-priority positions
3. **Plan ahead:** Consider which positions you'll need in upcoming rounds
4. **Monitor market values:** Compare suggested budgets to actual market prices
5. **Stay flexible:** Adapt strategy based on available players and competition

## Advanced Strategy

### Tiebreaker Preparation
- Keep extra budget for high-priority positions that might go to tiebreakers
- High-priority positions often have more competition
- Plan for 10-20% above suggested budget for crucial positions

### Market Analysis
- Compare your spending to position averages shown in the planner
- Red spending indicators mean you've spent above market average
- Green indicators show you've gotten good value

### Balance Management  
- Always maintain minimum balance per remaining round
- The "Available for next round" calculation prevents overspending
- Use the 80% rule: don't spend more than 80% of safe spending amount

This priority system helps ensure you build a competitive, well-balanced squad while managing your budget effectively throughout the auction process.
