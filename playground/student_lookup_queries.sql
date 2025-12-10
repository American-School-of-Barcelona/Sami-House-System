-- Student Lookup Queries
-- SQLite3 syntax

-- ============================================
-- 1. Find a specific student's house by name
-- ============================================
-- Search by last name
SELECT
    s.fname || ' ' || s.lname AS student_name,
    s.email,
    h.house_name,
    h.color,
    cy.class_name,
    cy.grad_year
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
WHERE s.lname LIKE '%Chen%'  -- Replace 'Chen' with the last name you're searching for
ORDER BY s.lname, s.fname;

-- ============================================
-- 2. Find a student by email
-- ============================================
SELECT
    s.fname || ' ' || s.lname AS student_name,
    s.email,
    h.house_name,
    h.color,
    cy.class_name,
    cy.grad_year
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
WHERE s.email = 'schen@school.edu';  -- Replace with the email you're searching for

-- ============================================
-- 3. Find students by first name (partial match)
-- ============================================
SELECT
    s.fname || ' ' || s.lname AS student_name,
    s.email,
    h.house_name,
    h.color,
    cy.class_name
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
WHERE s.fname LIKE '%Sophia%'  -- Replace 'Sophia' with the first name you're searching for
ORDER BY s.fname, s.lname;

-- ============================================
-- 4. Find all students by full name (partial match)
-- ============================================
SELECT
    s.fname || ' ' || s.lname AS student_name,
    s.email,
    h.house_name,
    h.color,
    cy.class_name,
    cy.grad_year
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
WHERE s.fname || ' ' || s.lname LIKE '%Marcus Williams%'  -- Replace with name
ORDER BY s.lname, s.fname;

-- ============================================
-- 5. List all students in a specific house
-- ============================================
SELECT
    s.fname || ' ' || s.lname AS student_name,
    s.email,
    cy.class_name,
    cy.grad_year
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
WHERE h.house_name = 'Athena'  -- Change to 'Poseidon', 'Artemis', or 'Apollo'
ORDER BY cy.display_order, s.lname, s.fname;

-- ============================================
-- 6. List all students with their houses (full roster)
-- ============================================
SELECT
    h.house_name,
    h.color,
    cy.class_name,
    s.fname || ' ' || s.lname AS student_name,
    s.email
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
ORDER BY h.house_name, cy.display_order, s.lname, s.fname;

-- ============================================
-- 7. Find multiple students by a list of emails
-- ============================================
SELECT
    s.fname || ' ' || s.lname AS student_name,
    s.email,
    h.house_name,
    h.color,
    cy.class_name
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
WHERE s.email IN ('schen@school.edu', 'zpatel@school.edu', 'ajohnson@school.edu')
ORDER BY h.house_name, s.lname;

-- ============================================
-- 8. Search students across all fields (universal search)
-- ============================================
SELECT
    s.fname || ' ' || s.lname AS student_name,
    s.email,
    h.house_name,
    h.color,
    cy.class_name,
    cy.grad_year
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
WHERE s.fname LIKE '%chen%'
   OR s.lname LIKE '%chen%'
   OR s.email LIKE '%chen%'
   OR h.house_name LIKE '%chen%'
ORDER BY s.lname, s.fname;

-- ============================================
-- 9. Find students in a specific house and grade
-- ============================================
SELECT
    s.fname || ' ' || s.lname AS student_name,
    s.email,
    h.house_name,
    cy.class_name
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
WHERE h.house_name = 'Athena'  -- Change house name
  AND cy.class_name = 'Senior'  -- Change to 'Junior', 'Sophomore', or 'Freshman'
ORDER BY s.lname, s.fname;

-- ============================================
-- 10. Count students by last name initial and house
-- ============================================
SELECT
    UPPER(SUBSTR(s.lname, 1, 1)) AS last_name_initial,
    h.house_name,
    COUNT(*) AS student_count
FROM STUDENTS s
JOIN HOUSES h ON s.house_id = h.house_id
GROUP BY last_name_initial, h.house_name
ORDER BY last_name_initial, h.house_name;
