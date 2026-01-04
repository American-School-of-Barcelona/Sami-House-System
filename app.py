"""
Flask Web Application for House Points System
No JavaScript - Pure HTML and Flask

Run with:
    python app.py
Then visit: http://localhost:5000
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
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

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'


# ============================================
# USER CLASS FOR FLASK-LOGIN
# ============================================

class User(UserMixin):
    """User class for Flask-Login"""
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role


@login_manager.user_loader
def load_user(user_id):
    """Load user from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, role FROM USERS WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    return None


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
# AUTHENTICATION ROUTES
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Get user from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password_hash, role FROM USERS WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()

        # Check if user exists and password is correct
        if user_data and check_password_hash(user_data[2], password):
            user = User(user_data[0], user_data[1], user_data[3])
            login_user(user)
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout current user"""
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))


# ============================================
# MAIN ROUTES
# ============================================

@app.route('/')
@login_required
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
@login_required
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
@login_required
def add_student():
    """Add new students"""
    if request.method == 'POST':
        # Get the number of students
        student_count = int(request.form.get('student_count', 1))

        added_students = []
        errors = []

        # Process each student
        for i in range(student_count):
            fname = request.form.get(f'fname_{i}')
            lname = request.form.get(f'lname_{i}')
            email = request.form.get(f'email_{i}')
            house_id = request.form.get(f'house_id_{i}')
            class_year_id = request.form.get(f'class_year_id_{i}')

            # Validate
            if not all([fname, lname, email, house_id, class_year_id]):
                errors.append(f'Student {i + 1}: All fields are required')
                continue

            try:
                # Add student to database
                student_id = db.add_student(fname, lname, email, int(house_id), int(class_year_id))
                added_students.append(f'{fname} {lname}')
            except Exception as e:
                errors.append(f'Student {i + 1} ({fname} {lname}): {str(e)}')

        # Show results
        if added_students:
            if len(added_students) == 1:
                flash(f'Successfully added {added_students[0]}!', 'success')
            else:
                flash(f'Successfully added {len(added_students)} students!', 'success')

        if errors:
            for error in errors:
                flash(error, 'error')

        if added_students:
            return redirect(url_for('students'))

    # Get houses and class years for the form
    houses = get_all_houses()
    class_years = get_all_class_years()

    return render_template('add_student.html', houses=houses, class_years=class_years)


@app.route('/events')
@login_required
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
@login_required
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


@app.route('/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    """Delete an event and all its results"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get event name for the flash message
        cursor.execute("SELECT event_desc FROM EVENTS WHERE event_id = ?", (event_id,))
        event = cursor.fetchone()
        event_name = event[0] if event else "Event"

        # Delete event results first (due to foreign key constraint)
        cursor.execute("DELETE FROM EVENT_RESULTS WHERE event_id = ?", (event_id,))

        # Delete the event
        cursor.execute("DELETE FROM EVENTS WHERE event_id = ?", (event_id,))

        conn.commit()
        conn.close()

        flash(f'Successfully deleted event: {event_name}', 'success')
    except Exception as e:
        flash(f'Error deleting event: {str(e)}', 'error')

    return redirect(url_for('events'))


@app.route('/add-event', methods=['GET', 'POST'])
@login_required
def add_event():
    """Add a new event with results"""
    if request.method == 'POST':
        # Get event data
        event_date = request.form.get('event_date')
        event_name = request.form.get('event_name')
        event_type = request.form.get('event_type')

        # If "other" is selected, use custom event type
        if event_type == 'other':
            custom_event_type = request.form.get('custom_event_type')
            if custom_event_type:
                event_type = custom_event_type.strip()

        # Get results for each house
        results = []
        houses = get_all_houses()

        for house_id, house_name, color in houses:
            points = request.form.get(f'points_{house_id}')
            rank = request.form.get(f'rank_{house_id}')

            if points and rank:
                results.append((int(house_id), int(points), int(rank)))

        # Validate
        if not all([event_date, event_name, event_type]):
            flash('Event date, name, and type are required!', 'error')
        elif len(results) == 0:
            flash('Please enter results for at least one house!', 'error')
        else:
            try:
                # Add event and results to database
                event_id = db.add_complete_event_with_results(
                    event_date, event_name, event_type, results
                )
                flash(f'Successfully added event: {event_name}!', 'success')
                return redirect(url_for('events'))
            except Exception as e:
                flash(f'Error adding event: {str(e)}', 'error')

    # Get houses for the form
    houses = get_all_houses()

    return render_template('add_event.html', houses=houses)


@app.route('/quick-points', methods=['GET', 'POST'])
@login_required
def quick_points():
    """Quick points input without creating an event"""
    if request.method == 'POST':
        # Get houses
        houses = get_all_houses()
        points_awarded = []

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            for house_id, house_name, color in houses:
                points = request.form.get(f'points_{house_id}')
                reason = request.form.get(f'reason_{house_id}', '').strip()

                # Only process if points were entered
                if points and points.strip():
                    points_value = int(points)
                    if points_value != 0:  # Allow both positive and negative values
                        # Create event entry for tracking
                        from datetime import date
                        event_date = date.today().strftime('%Y-%m-%d')

                        # For deductions, store as positive but with special event type
                        # The analysis queries will need to handle 'deduction' type by subtracting
                        if points_value < 0:
                            event_type = 'deduction'
                            event_name = reason if reason else 'Point Deduction'
                            stored_points = abs(points_value)  # Store absolute value
                        else:
                            event_type = 'quick_points'
                            event_name = reason if reason else 'Quick Points'
                            stored_points = points_value

                        # Insert event
                        cursor.execute("""
                            INSERT INTO EVENTS (event_date, event_desc, event_type)
                            VALUES (?, ?, ?)
                        """, (event_date, event_name, event_type))

                        event_id = cursor.lastrowid

                        # Insert event result with absolute value (to satisfy constraint)
                        cursor.execute("""
                            INSERT INTO EVENT_RESULTS (event_id, house_id, points_earned, rank)
                            VALUES (?, ?, ?, 1)
                        """, (event_id, house_id, stored_points))

                        # Format the message with + or - prefix
                        sign = '+' if points_value > 0 else ''
                        points_awarded.append(f"{house_name}: {sign}{points_value} points")

            conn.commit()

            if points_awarded:
                flash(f"Successfully applied points! {', '.join(points_awarded)}", 'success')
            else:
                flash('No points were applied. Please enter points for at least one house.', 'error')

        except Exception as e:
            conn.rollback()
            flash(f'Error awarding points: {str(e)}', 'error')
        finally:
            conn.close()

        return redirect(url_for('index'))

    # GET request - show form
    houses = get_all_houses()
    return render_template('quick_points.html', houses=houses)


@app.route('/edit-student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    """Edit an existing student"""
    if request.method == 'POST':
        # Get updated data
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
                # Update student in database
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE STUDENTS
                    SET fname = ?, lname = ?, email = ?, house_id = ?, class_year_id = ?
                    WHERE student_id = ?
                """, (fname, lname, email, int(house_id), int(class_year_id), student_id))

                conn.commit()
                conn.close()

                flash(f'Successfully updated {fname} {lname}!', 'success')
                return redirect(url_for('students'))
            except Exception as e:
                flash(f'Error updating student: {str(e)}', 'error')

    # GET request - show form with current data
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT student_id, fname, lname, email, house_id, class_year_id
        FROM STUDENTS
        WHERE student_id = ?
    """, (student_id,))

    student = cursor.fetchone()
    conn.close()

    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('students'))

    # Get houses and class years for the form
    houses = get_all_houses()
    class_years = get_all_class_years()

    return render_template('edit_student.html', student=student, houses=houses, class_years=class_years)


@app.route('/leaderboard')
@login_required
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
@login_required
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
