-- House Points Dashboard Database Schema
-- SQLite3 syntax

-- CLASS_YEARS: Reference table for student class levels
CREATE TABLE CLASS_YEARS (
    class_year_id INTEGER PRIMARY KEY AUTOINCREMENT,
    grad_year INTEGER NOT NULL UNIQUE,
    class_name TEXT NOT NULL,
    display_order INTEGER NOT NULL
);

-- HOUSES: The four house teams
CREATE TABLE HOUSES (
    house_id INTEGER PRIMARY KEY AUTOINCREMENT,
    house_name TEXT NOT NULL UNIQUE,
    logo_sq TEXT,
    logo_large TEXT,
    color TEXT
);

-- STUDENTS: Student roster with house and class assignments
CREATE TABLE STUDENTS (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fname TEXT NOT NULL,
    lname TEXT NOT NULL,
    email TEXT,
    house_id INTEGER NOT NULL,
    class_year_id INTEGER NOT NULL,
    FOREIGN KEY (house_id) REFERENCES HOUSES(house_id),
    FOREIGN KEY (class_year_id) REFERENCES CLASS_YEARS(class_year_id)
);

-- EVENTS: Individual competition events
CREATE TABLE EVENTS (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date TEXT NOT NULL,  -- Store as 'YYYY-MM-DD' format
    event_desc TEXT NOT NULL,
    event_type TEXT,
    created_at TEXT DEFAULT (datetime('now'))  -- Store as ISO8601 string
);

-- EVENT_RESULTS: Junction table storing house performance in each event
CREATE TABLE EVENT_RESULTS (
    event_id INTEGER NOT NULL,
    house_id INTEGER NOT NULL,
    points_earned INTEGER NOT NULL DEFAULT 0,
    rank INTEGER NOT NULL,
    PRIMARY KEY (event_id, house_id),
    FOREIGN KEY (event_id) REFERENCES EVENTS(event_id) ON DELETE CASCADE,
    FOREIGN KEY (house_id) REFERENCES HOUSES(house_id),
    CHECK (rank BETWEEN 1 AND 4),
    CHECK (points_earned >= 0)
);

-- Indexes for common queries
CREATE INDEX idx_student_house ON STUDENTS(house_id);
CREATE INDEX idx_student_class ON STUDENTS(class_year_id);
CREATE INDEX idx_event_date ON EVENTS(event_date);
CREATE INDEX idx_event_results_house ON EVENT_RESULTS(house_id);