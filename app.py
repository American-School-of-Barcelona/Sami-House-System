"""
Flask Web Application for House Points System
No JavaScript - Pure HTML and Flask

Run with:
    python app.py
Then visit: http://localhost:5000
"""

from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

# Import our database handler
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'playground'))
from database_insert_guide import HousePointsDatabase
from analysis_queries import HousePointsAnalyzer

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# Database path
DB_PATH = os.path.join('playground', 'testhouse.db')

# Initialize database handlers
db = HousePointsDatabase(DB_PATH)
analyzer = HousePointsAnalyzer(DB_PATH)


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_all_houses():
    """Get all houses from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT house_id, house_name, color FROM HOUSES ORDER BY house_name")
    houses = cursor.fetchall()
    conn.close()
    return houses


def get_all_class_years():
    """Get all class years from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT class_year_id, class_name, grad_year FROM CLASS_YEARS ORDER BY display_order")
    class_years = cursor.fetchall()
    conn.close()
    return class_years


# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    """Home page - shows winning house and leaderboard"""
    # Get winning house
    winner = analyzer.get_winning_house()

    # Get complete leaderboard
    leaderboard = analyzer.get_complete_leaderboard()

    # Get house standings with points ahead
    standings = analyzer.get_standings_with_points_ahead()

    return render_template('index.html',
                         winner=winner,
                         leaderboard=leaderboard,
                         standings=standings)


@app.route('/students')
def students():
    """View all students with search functionality"""
    search_query = request.args.get('search', '').strip()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if search_query:
        # Search by name or email
        query = """
        SELECT
            s.student_id,
            s.fname || ' ' || s.lname AS student_name,
            s.email,
            h.house_name,
            h.color,
            cy.class_name
        FROM STUDENTS s
        JOIN HOUSES h ON s.house_id = h.house_id
        JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
        WHERE s.fname || ' ' || s.lname LIKE ?
           OR s.email LIKE ?
           OR s.fname LIKE ?
           OR s.lname LIKE ?
        ORDER BY h.house_name, cy.display_order, s.lname, s.fname
        """
        search_pattern = f"%{search_query}%"
        cursor.execute(query, (search_pattern, search_pattern, search_pattern, search_pattern))
    else:
        # Get all students
        query = """
        SELECT
            s.student_id,
            s.fname || ' ' || s.lname AS student_name,
            s.email,
            h.house_name,
            h.color,
            cy.class_name
        FROM STUDENTS s
        JOIN HOUSES h ON s.house_id = h.house_id
        JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
        ORDER BY h.house_name, cy.display_order, s.lname, s.fname
        """
        cursor.execute(query)

    all_students = cursor.fetchall()
    conn.close()

    return render_template('students.html', students=all_students, search_query=search_query)


@app.route('/add-student', methods=['GET', 'POST'])
def add_student():
    """Add a new student"""
    if request.method == 'POST':
        # Get form data
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        house_id = request.form.get('house_id')
        class_year_id = request.form.get('class_year_id')

        # Validate
        if not all([fname, lname, email, house_id, class_year_id]):
            flash('All fields are required!', 'error')
        else:
            try:
                # Add student to database
                student_id = db.add_student(fname, lname, email, int(house_id), int(class_year_id))
                flash(f'Successfully added {fname} {lname}!', 'success')
                return redirect(url_for('students'))
            except Exception as e:
                flash(f'Error adding student: {str(e)}', 'error')

    # Get houses and class years for the form
    houses = get_all_houses()
    class_years = get_all_class_years()

    return render_template('add_student.html', houses=houses, class_years=class_years)


@app.route('/events')
def events():
    """View all events"""
    # Get all events with their results
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT
        e.event_id,
        e.event_date,
        e.event_desc,
        e.event_type,
        COUNT(er.house_id) as houses_participated
    FROM EVENTS e
    LEFT JOIN EVENT_RESULTS er ON e.event_id = er.event_id
    GROUP BY e.event_id
    ORDER BY e.event_date DESC
    """

    cursor.execute(query)
    all_events = cursor.fetchall()
    conn.close()

    return render_template('events.html', events=all_events)


@app.route('/event/<int:event_id>')
def event_details(event_id):
    """View details of a specific event"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get event info
    cursor.execute("""
        SELECT event_id, event_date, event_desc, event_type
        FROM EVENTS
        WHERE event_id = ?
    """, (event_id,))
    event = cursor.fetchone()

    # Get results for this event
    cursor.execute("""
        SELECT
            h.house_name,
            h.color,
            er.rank,
            er.points_earned
        FROM EVENT_RESULTS er
        JOIN HOUSES h ON er.house_id = h.house_id
        WHERE er.event_id = ?
        ORDER BY er.rank
    """, (event_id,))
    results = cursor.fetchall()

    conn.close()

    return render_template('event_details.html', event=event, results=results)


@app.route('/add-event', methods=['GET', 'POST'])
def add_event():
    """Add a new event with results"""
    if request.method == 'POST':
        # Get event data
        event_date = request.form.get('event_date')
        event_desc = request.form.get('event_desc')
        event_type = request.form.get('event_type')

        # Get results for each house
        results = []
        houses = get_all_houses()

        for house_id, house_name, color in houses:
            points = request.form.get(f'points_{house_id}')
            rank = request.form.get(f'rank_{house_id}')

            if points and rank:
                results.append((int(house_id), int(points), int(rank)))

        # Validate
        if not all([event_date, event_desc, event_type]):
            flash('Event date, description, and type are required!', 'error')
        elif len(results) == 0:
            flash('Please enter results for at least one house!', 'error')
        else:
            try:
                # Add event and results to database
                event_id = db.add_complete_event_with_results(
                    event_date, event_desc, event_type, results
                )
                flash(f'Successfully added event: {event_desc}!', 'success')
                return redirect(url_for('events'))
            except Exception as e:
                flash(f'Error adding event: {str(e)}', 'error')

    # Get houses for the form
    houses = get_all_houses()

    return render_template('add_event.html', houses=houses)


@app.route('/leaderboard')
def leaderboard():
    """Full leaderboard page"""
    # Get complete leaderboard
    leaderboard = analyzer.get_complete_leaderboard()

    # Get students by house standing
    students_by_standing = analyzer.get_students_by_house_standing()

    return render_template('leaderboard.html',
                         leaderboard=leaderboard,
                         students_by_standing=students_by_standing)


@app.route('/winning-house')
def winning_house():
    """Detailed winning house page"""
    # Get winning house
    winner = analyzer.get_winning_house()

    # Get students in winning house
    winning_students = analyzer.get_students_in_winning_house()

    # Get winning house students grouped by grade
    students_by_grade = analyzer.get_winning_house_students_by_grade()

    return render_template('winning_house.html',
                         winner=winner,
                         winning_students=winning_students,
                         students_by_grade=students_by_grade)


# ============================================
# RUN APP
# ============================================

if __name__ == '__main__':
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"Warning: Database not found at {DB_PATH}")
        print("Please create the database first using the schema and test data files.")
    else:
        print(f"Using database: {DB_PATH}")

    app.run(debug=True, host='0.0.0.0', port=5000)
