"""
Test Query 11 - Get Current Winning House
"""
import os
import sys

# Add the current directory to the path so we can import analysis_queries
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analysis_queries import HousePointsAnalyzer

# Initialize analyzer with the database
db_path = os.path.join(os.path.dirname(__file__), 'testhouse.db')

print(f"Database path: {db_path}")
print(f"Database exists: {os.path.exists(db_path)}")
print()

# Create analyzer instance
analyzer = HousePointsAnalyzer(db_path)

# Test Query 11 - Get Winning House
print("="*60)
print("QUERY 11: CURRENT WINNING HOUSE")
print("="*60)

try:
    result = analyzer.get_winning_house()

    if result:
        winning_house, color, total_points, events_participated, first_place_wins = result
        print(f"Winning House: {winning_house}")
        print(f"Color: {color}")
        print(f"Total Points: {total_points}")
        print(f"Events Participated: {events_participated}")
        print(f"First Place Wins: {first_place_wins}")
    else:
        print("No results found")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("="*60)
print()

# Also test Query 13 - Simple Winner Check
print("="*60)
print("QUERY 13: SIMPLE WINNER NAME")
print("="*60)

try:
    winner_name = analyzer.get_winner_name()
    print(f"Winner: {winner_name}")
except Exception as e:
    print(f"Error: {e}")

print("="*60)
print()

# Also test Query 12 - Standings with Points Ahead
print("="*60)
print("QUERY 12: HOUSE STANDINGS WITH POINTS AHEAD")
print("="*60)

try:
    standings = analyzer.get_standings_with_points_ahead()
    for rank, house_name, color, total_points, points_ahead in standings:
        if points_ahead is not None:
            print(f"{rank}. {house_name} ({color}): {total_points} points (ahead by {points_ahead})")
        else:
            print(f"{rank}. {house_name} ({color}): {total_points} points")
except Exception as e:
    print(f"Error: {e}")

print("="*60)
