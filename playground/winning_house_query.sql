-- Query to find which house is currently winning
-- SQLite3 syntax

-- ============================================
-- Current Winning House
-- ============================================
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
LIMIT 1;

-- ============================================
-- Current House Standings (Top to Bottom)
-- ============================================
SELECT
    ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(er.points_earned), 0) DESC) AS rank,
    h.house_name,
    h.color,
    COALESCE(SUM(er.points_earned), 0) AS total_points,
    COALESCE(SUM(er.points_earned), 0) -
        LEAD(COALESCE(SUM(er.points_earned), 0)) OVER (ORDER BY COALESCE(SUM(er.points_earned), 0) DESC) AS points_ahead
FROM HOUSES h
LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
GROUP BY h.house_id, h.house_name, h.color
ORDER BY total_points DESC;

-- ============================================
-- Simple Winner Check (just the name)
-- ============================================
SELECT h.house_name
FROM HOUSES h
LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
GROUP BY h.house_id, h.house_name
ORDER BY COALESCE(SUM(er.points_earned), 0) DESC
LIMIT 1;
