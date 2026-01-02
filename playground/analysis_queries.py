"""
House Points Analysis Queries - Python Version
SQLite3 with Python

Usage:
    import sqlite3
    from analysis_queries import HousePointsAnalyzer

    analyzer = HousePointsAnalyzer('path/to/your/database.db')
    results = analyzer.get_total_points_by_house()
    for row in results:
        print(row)
"""

import sqlite3
from typing import List, Tuple, Any


class HousePointsAnalyzer:
    """Analyzer class for house points database queries"""

    def __init__(self, db_path: str):
        """
        Initialize the analyzer with a database path

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path

    def _execute_query(self, query: str, params: tuple = ()) -> List[Tuple]:
        """
        Execute a query and return results

        Args:
            query: SQL query string
            params: Query parameters for parameterized queries

        Returns:
            List of tuples containing query results
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results

    # ============================================
    # 1. Total points by house (overall standings)
    # ============================================
    def get_total_points_by_house(self) -> List[Tuple]:
        """
        Get total points for each house with overall standings

        Returns:
            List of tuples: (house_name, color, total_points, events_participated)
        """
        query = """
        SELECT
            h.house_name,
            h.color,
            COALESCE(SUM(
                CASE
                    WHEN e.event_type = 'deduction' THEN -er.points_earned
                    ELSE er.points_earned
                END
            ), 0) AS total_points,
            COUNT(er.event_id) AS events_participated
        FROM HOUSES h
        LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
        LEFT JOIN EVENTS e ON er.event_id = e.event_id
        GROUP BY h.house_id, h.house_name, h.color
        ORDER BY total_points DESC
        """
        return self._execute_query(query)

    # ============================================
    # 2. Points breakdown by house and event
    # ============================================
    def get_points_breakdown_by_event(self) -> List[Tuple]:
        """
        Get detailed breakdown of points by house and event

        Returns:
            List of tuples: (house_name, event_date, event_desc, event_type, points_earned, rank)
        """
        query = """
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
        ORDER BY e.event_date, er.rank
        """
        return self._execute_query(query)

    # ============================================
    # 3. House performance by event type
    # ============================================
    def get_performance_by_event_type(self) -> List[Tuple]:
        """
        Get house performance grouped by event type (sports, academic, arts)

        Returns:
            List of tuples: (house_name, event_type, points_in_category, events_in_category, avg_points_per_event)
        """
        query = """
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
        ORDER BY e.event_type, points_in_category DESC
        """
        return self._execute_query(query)

    # ============================================
    # 4. Number of wins by house (1st place finishes)
    # ============================================
    def get_wins_by_house(self) -> List[Tuple]:
        """
        Get number of first place finishes by house

        Returns:
            List of tuples: (house_name, first_place_finishes, points_from_wins)
        """
        query = """
        SELECT
            h.house_name,
            COUNT(*) AS first_place_finishes,
            SUM(er.points_earned) AS points_from_wins
        FROM EVENT_RESULTS er
        JOIN HOUSES h ON er.house_id = h.house_id
        WHERE er.rank = 1
        GROUP BY h.house_id, h.house_name
        ORDER BY first_place_finishes DESC
        """
        return self._execute_query(query)

    # ============================================
    # 5. Average rank by house (lower is better)
    # ============================================
    def get_average_rank_by_house(self) -> List[Tuple]:
        """
        Get average rank for each house (lower is better)

        Returns:
            List of tuples: (house_name, average_rank, events_participated)
        """
        query = """
        SELECT
            h.house_name,
            ROUND(AVG(er.rank), 2) AS average_rank,
            COUNT(*) AS events_participated
        FROM EVENT_RESULTS er
        JOIN HOUSES h ON er.house_id = h.house_id
        GROUP BY h.house_id, h.house_name
        ORDER BY average_rank ASC
        """
        return self._execute_query(query)

    # ============================================
    # 6. Student count by house and class year
    # ============================================
    def get_student_count_by_house_and_year(self) -> List[Tuple]:
        """
        Get student count grouped by house and class year

        Returns:
            List of tuples: (house_name, class_name, student_count)
        """
        query = """
        SELECT
            h.house_name,
            cy.class_name,
            COUNT(s.student_id) AS student_count
        FROM HOUSES h
        LEFT JOIN STUDENTS s ON h.house_id = s.house_id
        LEFT JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
        GROUP BY h.house_id, cy.class_year_id
        ORDER BY h.house_name, cy.display_order
        """
        return self._execute_query(query)

    # ============================================
    # 7. Total students per house
    # ============================================
    def get_total_students_per_house(self) -> List[Tuple]:
        """
        Get total student count for each house

        Returns:
            List of tuples: (house_name, total_students)
        """
        query = """
        SELECT
            h.house_name,
            COUNT(s.student_id) AS total_students
        FROM HOUSES h
        LEFT JOIN STUDENTS s ON h.house_id = s.house_id
        GROUP BY h.house_id, h.house_name
        ORDER BY total_students DESC
        """
        return self._execute_query(query)

    # ============================================
    # 8. Recent events with results (last 5 events)
    # ============================================
    def get_recent_events(self, limit: int = 20) -> List[Tuple]:
        """
        Get recent events with their results

        Args:
            limit: Number of results to return (default 20 for 5 events * 4 houses)

        Returns:
            List of tuples: (event_date, event_desc, event_type, house_name, rank, points_earned)
        """
        query = """
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
        LIMIT ?
        """
        return self._execute_query(query, (limit,))

    # ============================================
    # 9. Points per student ratio (efficiency metric)
    # ============================================
    def get_points_per_student_ratio(self) -> List[Tuple]:
        """
        Get efficiency metric showing points per student for each house

        Returns:
            List of tuples: (house_name, student_count, total_points, points_per_student)
        """
        query = """
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
        ORDER BY points_per_student DESC
        """
        return self._execute_query(query)

    # ============================================
    # 10. Complete leaderboard with rankings
    # ============================================
    def get_complete_leaderboard(self) -> List[Tuple]:
        """
        Get complete leaderboard with detailed rankings

        Returns:
            List of tuples: (current_rank, house_name, color, total_points, events_participated,
                           wins, second_place, third_place, fourth_place)
        """
        query = """
        SELECT
            ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(
                CASE
                    WHEN e.event_type = 'deduction' THEN -er.points_earned
                    ELSE er.points_earned
                END
            ), 0) DESC) AS current_rank,
            h.house_name,
            h.color,
            COALESCE(SUM(
                CASE
                    WHEN e.event_type = 'deduction' THEN -er.points_earned
                    ELSE er.points_earned
                END
            ), 0) AS total_points,
            COUNT(DISTINCT er.event_id) AS events_participated,
            SUM(CASE WHEN er.rank = 1 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN er.rank = 2 THEN 1 ELSE 0 END) AS second_place,
            SUM(CASE WHEN er.rank = 3 THEN 1 ELSE 0 END) AS third_place,
            SUM(CASE WHEN er.rank = 4 THEN 1 ELSE 0 END) AS fourth_place
        FROM HOUSES h
        LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
        LEFT JOIN EVENTS e ON er.event_id = e.event_id
        GROUP BY h.house_id, h.house_name, h.color
        ORDER BY total_points DESC
        """
        return self._execute_query(query)

    # ============================================
    # 11. Current Winning House
    # ============================================
    def get_winning_house(self) -> Tuple:
        """
        Get the current winning house

        Returns:
            Tuple: (winning_house, color, total_points, events_participated, first_place_wins)
        """
        query = """
        SELECT
            h.house_name AS winning_house,
            h.color,
            COALESCE(SUM(
                CASE
                    WHEN e.event_type = 'deduction' THEN -er.points_earned
                    ELSE er.points_earned
                END
            ), 0) AS total_points,
            COUNT(DISTINCT er.event_id) AS events_participated,
            SUM(CASE WHEN er.rank = 1 THEN 1 ELSE 0 END) AS first_place_wins
        FROM HOUSES h
        LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
        LEFT JOIN EVENTS e ON er.event_id = e.event_id
        GROUP BY h.house_id, h.house_name, h.color
        ORDER BY total_points DESC
        LIMIT 1
        """
        results = self._execute_query(query)
        return results[0] if results else None

    # ============================================
    # 12. Current House Standings with Points Ahead
    # ============================================
    def get_standings_with_points_ahead(self) -> List[Tuple]:
        """
        Get house standings showing how many points each house is ahead of the next

        Returns:
            List of tuples: (rank, house_name, color, total_points, points_ahead)
        """
        query = """
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
        ORDER BY total_points DESC
        """
        return self._execute_query(query)

    # ============================================
    # 13. Simple Winner Check (just the name)
    # ============================================
    def get_winner_name(self) -> str:
        """
        Get just the name of the winning house

        Returns:
            String: Name of the winning house
        """
        query = """
        SELECT h.house_name
        FROM HOUSES h
        LEFT JOIN EVENT_RESULTS er ON h.house_id = er.house_id
        GROUP BY h.house_id, h.house_name
        ORDER BY COALESCE(SUM(er.points_earned), 0) DESC
        LIMIT 1
        """
        results = self._execute_query(query)
        return results[0][0] if results else None

    # ============================================
    # 14. All students ranked by their house's total points
    # ============================================
    def get_all_students_ranked(self) -> List[Tuple]:
        """
        Get all students ranked by their house's total points

        Returns:
            List of tuples: (overall_rank, student_name, email, house_name, color,
                           class_name, house_total_points, house_rank)
        """
        query = """
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
        ORDER BY house_total_points DESC, h.house_name, cy.display_order, s.lname, s.fname
        """
        return self._execute_query(query)

    # ============================================
    # 15. Students in the winning house (1st place)
    # ============================================
    def get_students_in_winning_house(self) -> List[Tuple]:
        """
        Get all students in the winning house

        Returns:
            List of tuples: (student_name, email, house_name, color, class_name,
                           grad_year, house_total_points)
        """
        query = """
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
        ORDER BY cy.display_order, s.lname, s.fname
        """
        return self._execute_query(query)

    # ============================================
    # 16. Students by house standing
    # ============================================
    def get_students_by_house_standing(self) -> List[Tuple]:
        """
        Get all students organized by their house's standing

        Returns:
            List of tuples: (house_standing, house_name, color, total_points,
                           class_name, student_name, email)
        """
        query = """
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
        ORDER BY house_standings.rank, cy.display_order, s.lname, s.fname
        """
        return self._execute_query(query)

    # ============================================
    # 17. Students in top 2 houses
    # ============================================
    def get_students_in_top_2_houses(self) -> List[Tuple]:
        """
        Get all students in the top 2 houses

        Returns:
            List of tuples: (house_standing, house_name, color, total_points,
                           student_name, email, class_name)
        """
        query = """
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
        ORDER BY house_standings.rank, cy.display_order, s.lname, s.fname
        """
        return self._execute_query(query)

    # ============================================
    # 18. Count of students in each house standing position
    # ============================================
    def get_student_count_by_standing(self) -> List[Tuple]:
        """
        Get count of students in each house standing position

        Returns:
            List of tuples: (house_standing, house_name, color, total_points, student_count)
        """
        query = """
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
        ORDER BY house_standings.rank
        """
        return self._execute_query(query)

    # ============================================
    # 19. Students in winning house grouped by grade level
    # ============================================
    def get_winning_house_students_by_grade(self) -> List[Tuple]:
        """
        Get students in winning house grouped by grade level

        Returns:
            List of tuples: (class_name, grad_year, student_count, students)
        """
        query = """
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
        ORDER BY cy.display_order
        """
        return self._execute_query(query)

    # ============================================
    # 20. Winning house details with all student info
    # ============================================
    def get_winning_house_details(self) -> List[Tuple]:
        """
        Get comprehensive details about the winning house including all students

        Returns:
            List of tuples: (title, points, first_place_wins, total_students,
                           class_name, student_name, email)
        """
        query = """
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
        ORDER BY cy.display_order, s.lname, s.fname
        """
        return self._execute_query(query)


# Example usage
if __name__ == "__main__":
    # Initialize analyzer with your database path
    analyzer = HousePointsAnalyzer('house_points.db')

    # Example: Get winning house
    winner = analyzer.get_winning_house()
    if winner:
        print(f"Winning House: {winner[0]} ({winner[1]})")
        print(f"Total Points: {winner[2]}")
        print(f"First Place Wins: {winner[4]}")

    print("\n" + "="*50)

    # Example: Get complete leaderboard
    print("\nComplete Leaderboard:")
    leaderboard = analyzer.get_complete_leaderboard()
    for rank, house_name, color, points, events, wins, second, third, fourth in leaderboard:
        print(f"{rank}. {house_name} ({color}) - {points} points")
        print(f"   Wins: {wins}, 2nd: {second}, 3rd: {third}, 4th: {fourth}")

    print("\n" + "="*50)

    # Example: Get students in winning house
    print("\nStudents in Winning House:")
    winning_students = analyzer.get_students_in_winning_house()
    for student_name, email, house, color, grade, year, points in winning_students:
        print(f"  {student_name} ({grade}) - {email}")
