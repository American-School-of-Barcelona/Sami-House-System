"""
Test script to fetch the winning house from the database
"""
import sqlite3
import sys
import os

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, 'testhouse.db')

print(f"Connecting to database: {db_path}")
print(f"Database exists: {os.path.exists(db_path)}")
print()

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Query to get winning house
query = """
SELECT
    h.house_name AS winning_house,
    h.color,
    COALESCE(SUM(er.points_earned), 0) AS total_points,
    COUNT(DISTINCT er.event_id) AS events_participated,
    SUM(CASE WHEN er.rank = 1 THEN 1 ELSE 0 END) AS first_place_wins
FROM HOUSES h
LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
GROUP BY h.house_id, h.house_name, h.color
ORDER BY total_points DESC
LIMIT 1
"""

cursor.execute(query)
result = cursor.fetchone()

if result:
    house_name, color, total_points, events_participated, first_place_wins = result
    print('='*60)
    print('WINNING HOUSE')
    print('='*60)
    print(f'House Name: {house_name}')
    print(f'Color: {color}')
    print(f'Total Points: {total_points}')
    print(f'Events Participated: {events_participated}')
    print(f'First Place Wins: {first_place_wins}')
    print('='*60)
    print()

    # Also show all house standings
    print('ALL HOUSE STANDINGS')
    print('='*60)

    standings_query = """
    SELECT
        ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(er.points_earned), 0) DESC) AS rank,
        h.house_name,
        h.color,
        COALESCE(SUM(er.points_earned), 0) AS total_points
    FROM HOUSES h
    LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
    GROUP BY h.house_id, h.house_name, h.color
    ORDER BY total_points DESC
    """

    cursor.execute(standings_query)
    standings = cursor.fetchall()

    for rank, name, color, points in standings:
        print(f'{rank}. {name} ({color}): {points} points')

    print('='*60)
else:
    print('No results found')

conn.close()
