"""
Guide to Adding Data to SQLite Database using Python

This file demonstrates how to INSERT data into your house points database
"""

import sqlite3
from datetime import datetime


class HousePointsDatabase:
    """Class to handle database operations for the House Points system"""

    def __init__(self, db_path: str):
        """
        Initialize database connection

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path

    def _get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)

    # ============================================
    # ADDING STUDENTS
    # ============================================

    def add_student(self, fname: str, lname: str, email: str, house_id: int, class_year_id: int):
        """
        Add a single student to the database

        Args:
            fname: First name
            lname: Last name
            email: Email address
            house_id: ID of the house (1=Athena, 2=Poseidon, 3=Artemis, 4=Apollo)
            class_year_id: ID of the class year (1=Senior, 2=Junior, 3=Sophomore, 4=Freshman)

        Returns:
            int: The ID of the newly created student
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # SQL INSERT statement with placeholders (?)
        query = """
        INSERT INTO STUDENTS (fname, lname, email, house_id, class_year_id)
        VALUES (?, ?, ?, ?, ?)
        """

        # Execute with parameters to prevent SQL injection
        cursor.execute(query, (fname, lname, email, house_id, class_year_id))

        # Get the ID of the newly inserted student
        student_id = cursor.lastrowid

        # IMPORTANT: Commit to save changes
        conn.commit()
        conn.close()

        print(f"✓ Added student: {fname} {lname} (ID: {student_id})")
        return student_id

    def add_multiple_students(self, students_list: list):
        """
        Add multiple students at once (more efficient)

        Args:
            students_list: List of tuples [(fname, lname, email, house_id, class_year_id), ...]

        Example:
            students = [
                ('John', 'Doe', 'jdoe@school.edu', 1, 2),
                ('Jane', 'Smith', 'jsmith@school.edu', 2, 3)
            ]
            db.add_multiple_students(students)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO STUDENTS (fname, lname, email, house_id, class_year_id)
        VALUES (?, ?, ?, ?, ?)
        """

        # executemany() is more efficient for bulk inserts
        cursor.executemany(query, students_list)

        conn.commit()
        conn.close()

        print(f"✓ Added {len(students_list)} students")

    # ============================================
    # ADDING EVENTS
    # ============================================

    def add_event(self, event_date: str, event_desc: str, event_type: str):
        """
        Add a new event to the database

        Args:
            event_date: Date in 'YYYY-MM-DD' format
            event_desc: Description of the event
            event_type: Type ('sports', 'academic', 'arts', etc.)

        Returns:
            int: The ID of the newly created event
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO EVENTS (event_date, event_desc, event_type)
        VALUES (?, ?, ?)
        """

        cursor.execute(query, (event_date, event_desc, event_type))
        event_id = cursor.lastrowid

        conn.commit()
        conn.close()

        print(f"✓ Added event: {event_desc} (ID: {event_id})")
        return event_id

    # ============================================
    # ADDING EVENT RESULTS
    # ============================================

    def add_event_result(self, event_id: int, house_id: int, points_earned: int, rank: int):
        """
        Add a result for a house in an event

        Args:
            event_id: ID of the event
            house_id: ID of the house
            points_earned: Points earned (must be >= 0)
            rank: Placement rank (1-4)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO EVENT_RESULTS (event_id, house_id, points_earned, rank)
        VALUES (?, ?, ?, ?)
        """

        cursor.execute(query, (event_id, house_id, points_earned, rank))

        conn.commit()
        conn.close()

        print(f"✓ Added result: Event {event_id}, House {house_id}, Rank {rank}, Points {points_earned}")

    def add_complete_event_with_results(self, event_date: str, event_desc: str, event_type: str,
                                       results: list):
        """
        Add an event and all its results in one transaction

        Args:
            event_date: Date in 'YYYY-MM-DD' format
            event_desc: Description of the event
            event_type: Type of event
            results: List of tuples [(house_id, points_earned, rank), ...]

        Example:
            results = [
                (1, 400, 1),  # Athena: 400 points, 1st place
                (2, 300, 2),  # Poseidon: 300 points, 2nd place
                (3, 200, 3),  # Artemis: 200 points, 3rd place
                (4, 100, 4)   # Apollo: 100 points, 4th place
            ]
            db.add_complete_event_with_results('2024-12-01', 'House Quiz', 'academic', results)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Insert the event
            event_query = """
            INSERT INTO EVENTS (event_date, event_desc, event_type)
            VALUES (?, ?, ?)
            """
            cursor.execute(event_query, (event_date, event_desc, event_type))
            event_id = cursor.lastrowid

            # Insert all results
            results_query = """
            INSERT INTO EVENT_RESULTS (event_id, house_id, points_earned, rank)
            VALUES (?, ?, ?, ?)
            """

            # Add event_id to each result tuple
            results_with_event_id = [(event_id, house_id, points, rank)
                                    for house_id, points, rank in results]

            cursor.executemany(results_query, results_with_event_id)

            # Commit everything at once
            conn.commit()

            print(f"✓ Added event '{event_desc}' with {len(results)} results")
            return event_id

        except Exception as e:
            # If anything fails, rollback (undo) all changes
            conn.rollback()
            print(f"✗ Error adding event: {e}")
            raise

        finally:
            conn.close()

    # ============================================
    # HELPER METHODS - Get IDs by Name
    # ============================================

    def get_house_id_by_name(self, house_name: str):
        """Get house ID by house name"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT house_id FROM HOUSES WHERE house_name = ?", (house_name,))
        result = cursor.fetchone()

        conn.close()
        return result[0] if result else None

    def get_class_year_id_by_name(self, class_name: str):
        """Get class year ID by class name"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT class_year_id FROM CLASS_YEARS WHERE class_name = ?", (class_name,))
        result = cursor.fetchone()

        conn.close()
        return result[0] if result else None

    # ============================================
    # UPDATE DATA
    # ============================================

    def update_student_house(self, student_id: int, new_house_id: int):
        """
        Update a student's house assignment

        Args:
            student_id: ID of the student
            new_house_id: New house ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
        UPDATE STUDENTS
        SET house_id = ?
        WHERE student_id = ?
        """

        cursor.execute(query, (new_house_id, student_id))
        conn.commit()
        conn.close()

        print(f"✓ Updated student {student_id} to house {new_house_id}")

    def update_event_result_points(self, event_id: int, house_id: int, new_points: int):
        """
        Update points for a specific event result

        Args:
            event_id: ID of the event
            house_id: ID of the house
            new_points: New points value
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
        UPDATE EVENT_RESULTS
        SET points_earned = ?
        WHERE event_id = ? AND house_id = ?
        """

        cursor.execute(query, (new_points, event_id, house_id))
        conn.commit()
        conn.close()

        print(f"✓ Updated points for Event {event_id}, House {house_id} to {new_points}")

    # ============================================
    # DELETE DATA
    # ============================================

    def delete_student(self, student_id: int):
        """Delete a student by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM STUDENTS WHERE student_id = ?", (student_id,))
        conn.commit()
        conn.close()

        print(f"✓ Deleted student {student_id}")

    def delete_event(self, event_id: int):
        """
        Delete an event (this will also delete all related results
        because of the ON DELETE CASCADE constraint)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM EVENTS WHERE event_id = ?", (event_id,))
        conn.commit()
        conn.close()

        print(f"✓ Deleted event {event_id} and all its results")


# ============================================
# USAGE EXAMPLES
# ============================================

if __name__ == "__main__":
    # Initialize the database handler
    db = HousePointsDatabase('testhouse.db')

    print("\n" + "="*60)
    print("EXAMPLE 1: Adding a Single Student")
    print("="*60)

    # Add a single student to Athena house (house_id=1), Senior year (class_year_id=1)
    student_id = db.add_student(
        fname='Emily',
        lname='Parker',
        email='eparker@school.edu',
        house_id=1,  # Athena
        class_year_id=1  # Senior
    )

    print("\n" + "="*60)
    print("EXAMPLE 2: Adding Multiple Students at Once")
    print("="*60)

    new_students = [
        ('Michael', 'Anderson', 'manderson@school.edu', 2, 3),  # Poseidon, Sophomore
        ('Sarah', 'White', 'swhite@school.edu', 3, 2),          # Artemis, Junior
        ('Daniel', 'Harris', 'dharris@school.edu', 4, 4)        # Apollo, Freshman
    ]

    db.add_multiple_students(new_students)

    print("\n" + "="*60)
    print("EXAMPLE 3: Adding a Complete Event with Results")
    print("="*60)

    # Create a new event with all results
    event_results = [
        (1, 400, 1),  # Athena: 400 points, 1st place
        (3, 300, 2),  # Artemis: 300 points, 2nd place
        (4, 200, 3),  # Apollo: 200 points, 3rd place
        (2, 100, 4)   # Poseidon: 100 points, 4th place
    ]

    event_id = db.add_complete_event_with_results(
        event_date='2024-12-15',
        event_desc='Winter House Challenge',
        event_type='sports',
        results=event_results
    )

    print("\n" + "="*60)
    print("EXAMPLE 4: Adding Student Using House Name")
    print("="*60)

    # First get the house ID by name
    athena_id = db.get_house_id_by_name('Athena')
    senior_id = db.get_class_year_id_by_name('Senior')

    if athena_id and senior_id:
        db.add_student('Alex', 'Morgan', 'amorgan@school.edu', athena_id, senior_id)

    print("\n" + "="*60)
    print("EXAMPLE 5: Updating Existing Data")
    print("="*60)

    # Update a student's house
    # db.update_student_house(student_id=1, new_house_id=2)

    # Update event result points
    # db.update_event_result_points(event_id=1, house_id=1, new_points=450)

    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)
