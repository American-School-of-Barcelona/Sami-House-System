-- House Points Analysis Queries
-- SQLite3 syntax

-- ============================================
-- 1. Total points by house (overall standings)
-- ============================================
SELECT
    h.house_name,
    h.color,
    COALESCE(SUM(er.points_earned), 0) AS total_points,
    COUNT(er.event_id) AS events_participated
FROM HOUSES h
LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
GROUP BY h.house_id, h.house_name, h.color
ORDER BY total_points DESC;

-- ============================================
-- 2. Points breakdown by house and event
-- ============================================
SELECT
    h.house_name,
    e.event_date,
    e.event_desc,
    e.event_type,
    er.points_earned,
    er.rank
FROM EVENT_RESULTS er
JOIN HOUSES h ON er.house_id = h.house_id
JOIN EVENTS e ON er.event_id = e.event_id
ORDER BY e.event_date, er.rank;

-- ============================================
-- 3. House performance by event type
-- ============================================
SELECT
    h.house_name,
    e.event_type,
    SUM(er.points_earned) AS points_in_category,
    COUNT(*) AS events_in_category,
    ROUND(AVG(er.points_earned), 2) AS avg_points_per_event
FROM EVENT_RESULTS er
JOIN HOUSES h ON er.house_id = h.house_id
JOIN EVENTS e ON er.event_id = e.event_id
GROUP BY h.house_id, e.event_type
ORDER BY e.event_type, points_in_category DESC;

-- ============================================
-- 4. Number of wins by house (1st place finishes)
-- ============================================
SELECT
    h.house_name,
    COUNT(*) AS first_place_finishes,
    SUM(er.points_earned) AS points_from_wins
FROM EVENT_RESULTS er
JOIN HOUSES h ON er.house_id = h.house_id
WHERE er.rank = 1
GROUP BY h.house_id, h.house_name
ORDER BY first_place_finishes DESC;

-- ============================================
-- 5. Average rank by house (lower is better)
-- ============================================
SELECT
    h.house_name,
    ROUND(AVG(er.rank), 2) AS average_rank,
    COUNT(*) AS events_participated
FROM EVENT_RESULTS er
JOIN HOUSES h ON er.house_id = h.house_id
GROUP BY h.house_id, h.house_name
ORDER BY average_rank ASC;

-- ============================================
-- 6. Student count by house and class year
-- ============================================
SELECT
    h.house_name,
    cy.class_name,
    COUNT(s.student_id) AS student_count
FROM HOUSES h
LEFT JOIN STUDENTS s ON h.house_id = s.house_id
LEFT JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
GROUP BY h.house_id, cy.class_year_id
ORDER BY h.house_name, cy.display_order;

-- ============================================
-- 7. Total students per house
-- ============================================
SELECT
    h.house_name,
    COUNT(s.student_id) AS total_students
FROM HOUSES h
LEFT JOIN STUDENTS s ON h.house_id = s.house_id
GROUP BY h.house_id, h.house_name
ORDER BY total_students DESC;

-- ============================================
-- 8. Recent events with results (last 5 events)
-- ============================================
SELECT
    e.event_date,
    e.event_desc,
    e.event_type,
    h.house_name,
    er.rank,
    er.points_earned
FROM EVENTS e
JOIN EVENT_RESULTS er ON e.event_id = er.event_id
JOIN HOUSES h ON er.house_id = h.house_id
ORDER BY e.event_date DESC, er.rank ASC
LIMIT 20;  -- 5 events * 4 houses

-- ============================================
-- 9. Points per student ratio (efficiency metric)
-- ============================================
SELECT
    h.house_name,
    COUNT(DISTINCT s.student_id) AS student_count,
    COALESCE(SUM(er.points_earned), 0) AS total_points,
    CASE
        WHEN COUNT(DISTINCT s.student_id) > 0
        THEN ROUND(CAST(COALESCE(SUM(er.points_earned), 0) AS FLOAT) / COUNT(DISTINCT s.student_id), 2)
        ELSE 0
    END AS points_per_student
FROM HOUSES h
LEFT JOIN STUDENTS s ON h.house_id = s.house_id
LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
GROUP BY h.house_id, h.house_name
ORDER BY points_per_student DESC;

-- ============================================
-- 10. Complete leaderboard with rankings
-- ============================================
SELECT
    ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(er.points_earned), 0) DESC) AS current_rank,
    h.house_name,
    h.color,
    COALESCE(SUM(er.points_earned), 0) AS total_points,
    COUNT(DISTINCT er.event_id) AS events_participated,
    SUM(CASE WHEN er.rank = 1 THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN er.rank = 2 THEN 1 ELSE 0 END) AS second_place,
    SUM(CASE WHEN er.rank = 3 THEN 1 ELSE 0 END) AS third_place,
    SUM(CASE WHEN er.rank = 4 THEN 1 ELSE 0 END) AS fourth_place
FROM HOUSES h
LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
GROUP BY h.house_id, h.house_name, h.color
ORDER BY total_points DESC;

-- ============================================
-- 11. Current Winning House
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
-- 12. Current House Standings with Points Ahead
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
-- 13. Simple Winner Check (just the name)
-- ============================================
SELECT h.house_name
FROM HOUSES h
LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
GROUP BY h.house_id, h.house_name
ORDER BY COALESCE(SUM(er.points_earned), 0) DESC
LIMIT 1;

-- ============================================
-- 14. All students ranked by their house's total points
-- ============================================
SELECT
    ROW_NUMBER() OVER (ORDER BY house_total_points DESC, h.house_name, cy.display_order, s.lname) AS overall_rank,
    s.fname || ' ' || s.lname AS student_name,
    s.email,
    h.house_name,
    h.color,
    cy.class_name,
    house_total_points,
    house_rank
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
JOIN (
    SELECT
        h.house_id,
        COALESCE(SUM(er.points_earned), 0) AS house_total_points,
        ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(er.points_earned), 0) DESC) AS house_rank
    FROM HOUSES h
    LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
    GROUP BY h.house_id
) house_standings ON h.house_id = house_standings.house_id
ORDER BY house_total_points DESC, h.house_name, cy.display_order, s.lname, s.fname;

-- ============================================
-- 15. Students in the winning house (1st place)
-- ============================================
SELECT
    s.fname || ' ' || s.lname AS student_name,
    s.email,
    h.house_name,
    h.color,
    cy.class_name,
    cy.grad_year,
    house_standings.total_points AS house_total_points
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
JOIN (
    SELECT
        h.house_id,
        h.house_name,
        COALESCE(SUM(er.points_earned), 0) AS total_points,
        ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(er.points_earned), 0) DESC) AS rank
    FROM HOUSES h
    LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
    GROUP BY h.house_id, h.house_name
) house_standings ON h.house_id = house_standings.house_id
WHERE house_standings.rank = 1
ORDER BY cy.display_order, s.lname, s.fname;

-- ============================================
-- 16. Students by house standing (shows which place each student's house is in)
-- ============================================
SELECT
    house_standings.rank AS house_standing,
    h.house_name,
    h.color,
    house_standings.total_points,
    cy.class_name,
    s.fname || ' ' || s.lname AS student_name,
    s.email
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
JOIN (
    SELECT
        h.house_id,
        COALESCE(SUM(er.points_earned), 0) AS total_points,
        ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(er.points_earned), 0) DESC) AS rank
    FROM HOUSES h
    LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
    GROUP BY h.house_id
) house_standings ON h.house_id = house_standings.house_id
ORDER BY house_standings.rank, cy.display_order, s.lname, s.fname;

-- ============================================
-- 17. Students in top 2 houses
-- ============================================
SELECT
    house_standings.rank AS house_standing,
    h.house_name,
    h.color,
    house_standings.total_points,
    s.fname || ' ' || s.lname AS student_name,
    s.email,
    cy.class_name
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
JOIN (
    SELECT
        h.house_id,
        COALESCE(SUM(er.points_earned), 0) AS total_points,
        ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(er.points_earned), 0) DESC) AS rank
    FROM HOUSES h
    LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
    GROUP BY h.house_id
) house_standings ON h.house_id = house_standings.house_id
WHERE house_standings.rank <= 2
ORDER BY house_standings.rank, cy.display_order, s.lname, s.fname;

-- ============================================
-- 18. Count of students in each house standing position
-- ============================================
SELECT
    house_standings.rank AS house_standing,
    h.house_name,
    h.color,
    house_standings.total_points,
    COUNT(s.student_id) AS student_count
FROM HOUSES h
LEFT JOIN STUDENTS s ON h.house_id = s.house_id
JOIN (
    SELECT
        h.house_id,
        COALESCE(SUM(er.points_earned), 0) AS total_points,
        ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(er.points_earned), 0) DESC) AS rank
    FROM HOUSES h
    LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
    GROUP BY h.house_id
) house_standings ON h.house_id = house_standings.house_id
GROUP BY house_standings.rank, h.house_name, h.color, house_standings.total_points
ORDER BY house_standings.rank;

-- ============================================
-- 19. Students in winning house grouped by grade level
-- ============================================
SELECT
    cy.class_name,
    cy.grad_year,
    COUNT(s.student_id) AS student_count,
    GROUP_CONCAT(s.fname || ' ' || s.lname, ', ') AS students
FROM STUDENTS s
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
JOIN HOUSES h ON s.house_id = h.house_id
JOIN (
    SELECT
        h.house_id,
        ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(er.points_earned), 0) DESC) AS rank
    FROM HOUSES h
    LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
    GROUP BY h.house_id
) house_standings ON h.house_id = house_standings.house_id
WHERE house_standings.rank = 1
GROUP BY cy.class_year_id, cy.class_name, cy.grad_year
ORDER BY cy.display_order;

-- ============================================
-- 20. Winning house details with all student info
-- ============================================
SELECT
    'House Champion: ' || h.house_name AS title,
    house_standings.total_points AS points,
    house_standings.wins AS first_place_wins,
    COUNT(DISTINCT s.student_id) AS total_students,
    cy.class_name,
    s.fname || ' ' || s.lname AS student_name,
    s.email
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
JOIN (
    SELECT
        h.house_id,
        h.house_name,
        COALESCE(SUM(er.points_earned), 0) AS total_points,
        SUM(CASE WHEN er.rank = 1 THEN 1 ELSE 0 END) AS wins,
        ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(er.points_earned), 0) DESC) AS rank
    FROM HOUSES h
    LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
    GROUP BY h.house_id, h.house_name
) house_standings ON h.house_id = house_standings.house_id
WHERE house_standings.rank = 1
GROUP BY h.house_name, house_standings.total_points, house_standings.wins, cy.class_name, s.student_id, s.fname, s.lname, s.email
ORDER BY cy.display_order, s.lname, s.fname;
