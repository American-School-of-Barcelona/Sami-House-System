-- Sample Data for House Points Dashboard
-- SQLite3 syntax

-- Insert Class Years (current school year 2024-2025)
INSERT INTO CLASS_YEARS (grad_year, class_name, display_order) VALUES
(2025, 'Senior', 1),
(2026, 'Junior', 2),
(2027, 'Sophomore', 3),
(2028, 'Freshman', 4);

-- Insert Houses
INSERT INTO HOUSES (house_name, logo_sq, logo_large, color) VALUES
('Athena', 'athena_sq.png', 'athena_large.png', 'yellow'),
('Poseidon', 'poseidon_sq.png', 'poseidon_large.png', 'blue'),
('Artemis', 'artemis_sq.png', 'artemis_large.png', 'green'),
('Apollo', 'apollo_sq.png', 'apollo_large.png', 'red');

-- Insert Sample Students (mix across houses and years)
INSERT INTO STUDENTS (fname, lname, email, house_id, class_year_id) VALUES
-- Athena students
('Sophia', 'Chen', 'schen@school.edu', 1, 1),
('Marcus', 'Williams', 'mwilliams@school.edu', 1, 2),
('Elena', 'Rodriguez', 'erodriguez@school.edu', 1, 3),
('David', 'Kim', 'dkim@school.edu', 1, 4),

-- Poseidon students
('Zara', 'Patel', 'zpatel@school.edu', 2, 1),
('James', 'O''Connor', 'joconnor@school.edu', 2, 2),
('Maya', 'Thompson', 'mthompson@school.edu', 2, 3),
('Lucas', 'Garcia', 'lgarcia@school.edu', 2, 4),

-- Artemis students
('Isabella', 'Nguyen', 'inguyen@school.edu', 3, 1),
('Ethan', 'Brown', 'ebrown@school.edu', 3, 2),
('Olivia', 'Martinez', 'omartinez@school.edu', 3, 3),
('Noah', 'Lee', 'nlee@school.edu', 3, 4),

-- Apollo students
('Ava', 'Johnson', 'ajohnson@school.edu', 4, 1),
('Liam', 'Davis', 'ldavis@school.edu', 4, 2),
('Emma', 'Wilson', 'ewilson@school.edu', 4, 3),
('Mason', 'Taylor', 'mtaylor@school.edu', 4, 4);

-- Insert Events
INSERT INTO EVENTS (event_date, event_desc, event_type) VALUES
('2024-09-15', 'Knockout Pop-up', 'sports'),
('2024-10-22', 'House Trivia Contest', 'academic'),
('2024-11-08', 'House Karaoke Sing-off', 'arts');

-- Insert Event Results
-- Event 1: Knockout Pop-up (Artemis dominates athletics!)
INSERT INTO EVENT_RESULTS (event_id, house_id, points_earned, rank) VALUES
(1, 3, 400, 1),  -- Artemis wins
(1, 2, 300, 2),  -- Poseidon second
(1, 4, 200, 3),  -- Apollo third
(1, 1, 100, 4);  -- Athena fourth

-- Event 2: House Trivia Contest (Athena claims wisdom!)
INSERT INTO EVENT_RESULTS (event_id, house_id, points_earned, rank) VALUES
(2, 1, 400, 1),  -- Athena wins
(2, 4, 300, 2),  -- Apollo second
(2, 3, 200, 3),  -- Artemis third
(2, 2, 100, 4);  -- Poseidon fourth

-- Event 3: House Karaoke Sing-off (Apollo brings the music!)
INSERT INTO EVENT_RESULTS (event_id, house_id, points_earned, rank) VALUES
(3, 4, 400, 1),  -- Apollo wins
(3, 3, 300, 2),  -- Artemis second
(3, 1, 200, 3),  -- Athena third
(3, 2, 100, 4);  -- Poseidon fourth