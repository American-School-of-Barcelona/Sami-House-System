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
from werkzeug.utils import secure_filename
import sqlite3
import os
import shutil
import csv
import io
from datetime import datetime

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
    def __init__(self, user_id, email, role):
        self.id = user_id
        self.email = email
        self.role = role

    @property
    def username(self):
        """Backwards compatibility - return email as username"""
        return self.email


@login_manager.user_loader
def load_user(user_id):
    """Load user from database"""
    # Special case for guest user
    if user_id == 'guest':
        return User('guest', 'Guest', 'guest')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, email, role FROM USERS WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    return None


# ============================================
# HELPER FUNCTIONS
# ============================================

def admin_required(f):
    """Decorator to require admin role (blocks guest and rep users)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role in ['guest', 'rep']:
            flash('You need administrator access to view this page.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def rep_or_admin_required(f):
    """Decorator to require rep or admin role (blocks only guest users)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role == 'guest':
            flash('You need representative or administrator access to view this page.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


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


def get_executive_title(email):
    """Get the executive title for a given email from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title, role FROM AUTHORIZED_EXECUTIVES WHERE LOWER(email) = LOWER(?)", (email,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else email


def get_executive_role(email):
    """Get the role for a given email from database (admin or rep)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM AUTHORIZED_EXECUTIVES WHERE LOWER(email) = LOWER(?)", (email,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'admin'  # Default to admin for backwards compatibility


def suggest_house_for_student(first_name, last_name, grade, homeroom=None):
    """
    Suggest the best house for a new student based on:
    1. 9th graders -> their homeroom's house (9A=Artemis, 9B=Athena, 9C=Poseidon, 9D=Apollo)
    2. Sibling matching -> same house as existing student with same last name
    3. Balance -> house with fewest students

    Returns: (suggested_house_id, suggested_house_name, reason)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # PRIORITY 1: Check if 9th grader with homeroom
    if grade == '9' and homeroom:
        # Map homeroom to house: 9A=Artemis, 9B=Athena, 9C=Poseidon, 9D=Apollo
        homeroom_mapping = {
            '9A': 'Artemis',
            '9B': 'Athena',
            '9C': 'Poseidon',
            '9D': 'Apollo'
        }

        homeroom_upper = homeroom.upper()
        if homeroom_upper in homeroom_mapping:
            house_name = homeroom_mapping[homeroom_upper]
            # Get the house_id for this house
            cursor.execute("SELECT house_id FROM HOUSES WHERE house_name = ?", (house_name,))
            result = cursor.fetchone()

            if result:
                conn.close()
                return (result[0], house_name, f"9th grader in homeroom {homeroom_upper} - assigned to {house_name}")

    # PRIORITY 2: Check for siblings (same last name)
    cursor.execute("""
        SELECT s.house_id, h.house_name, s.fname
        FROM STUDENTS s
        JOIN HOUSES h ON s.house_id = h.house_id
        WHERE LOWER(s.lname) = LOWER(?) AND s.house_id IS NOT NULL
        LIMIT 1
    """, (last_name,))
    sibling = cursor.fetchone()

    if sibling:
        house_id, house_name, sibling_name = sibling
        conn.close()
        return (house_id, house_name, f"Sibling match - {sibling_name} {last_name} is in {house_name}")

    # PRIORITY 3: Balance houses - assign to house with fewest students
    cursor.execute("""
        SELECT s.house_id, h.house_name, COUNT(*) as count
        FROM STUDENTS s
        JOIN HOUSES h ON s.house_id = h.house_id
        WHERE s.house_id IS NOT NULL
        GROUP BY s.house_id, h.house_name
        ORDER BY count ASC
    """)
    house_counts = cursor.fetchall()
    conn.close()

    if house_counts:
        smallest_house_id = house_counts[0][0]
        smallest_house_name = house_counts[0][1]
        smallest_count = house_counts[0][2]
        return (smallest_house_id, smallest_house_name, f"Balanced distribution - {smallest_house_name} has fewest students ({smallest_count})")

    # Fallback: if no students exist yet, return None
    return (None, None, "No existing students to base assignment on")


def get_authorized_emails():
    """Get list of authorized executive emails from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM AUTHORIZED_EXECUTIVES")
    emails = [row[0] for row in cursor.fetchall()]
    conn.close()
    return emails


def get_all_authorized_executives():
    """Get all authorized executives with their titles"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT email, title, added_at FROM AUTHORIZED_EXECUTIVES ORDER BY added_at")
    executives = cursor.fetchall()
    conn.close()
    return executives




# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Get user from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, email, password_hash, role FROM USERS WHERE email = ?", (email,))
        user_data = cursor.fetchone()
        conn.close()

        # Check if user exists and password is correct
        if user_data and check_password_hash(user_data[2], password):
            user = User(user_data[0], user_data[1], user_data[3])
            login_user(user)
            title = get_executive_title(email)
            flash(f'Welcome back, {title}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html')


@app.route('/guest')
def guest_login():
    """Login as guest with limited access"""
    guest_user = User('guest', 'Guest', 'guest')
    login_user(guest_user)
    flash('Logged in as Guest. You have limited access to view-only pages.', 'success')
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register new user - restricted to executive members only"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Get authorized emails from database
        authorized_emails = get_authorized_emails()

        # Validate input
        if not email or not password or not confirm_password:
            flash('All fields are required', 'error')
        elif '@' not in email or '.' not in email:
            flash('Please enter a valid email address', 'error')
        elif not email.lower().endswith('@asbarcelona.com'):
            flash('Only @asbarcelona.com email addresses are allowed', 'error')
        elif email.lower() not in [e.lower() for e in authorized_emails]:
            flash('This email is not authorized to create an account. Only Student Council Executive members can register. Please use the Guest login instead.', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
        elif password != confirm_password:
            flash('Passwords do not match', 'error')
        else:
            # Check if email already exists
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM USERS WHERE email = ?", (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash('An account with this email already exists.', 'error')
                conn.close()
            else:
                # Create new user with correct role from database
                user_role = get_executive_role(email)
                password_hash = generate_password_hash(password)
                cursor.execute("""
                    INSERT INTO USERS (email, password_hash, role)
                    VALUES (?, ?, ?)
                """, (email, password_hash, user_role))
                conn.commit()
                conn.close()

                flash('Account created successfully! You can now log in.', 'success')
                return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    """Logout current user"""
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))


@app.route('/manage_executives', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_executives():
    """Manage authorized executive emails and titles"""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            new_email = request.form.get('new_email')
            new_title = request.form.get('new_title')
            new_role = request.form.get('new_role', 'admin')
            new_grade = request.form.get('new_grade', None)

            if not new_email or not new_title:
                flash('Email and title are required', 'error')
            elif '@' not in new_email or '.' not in new_email:
                flash('Please enter a valid email address', 'error')
            elif not new_email.lower().endswith('@asbarcelona.com'):
                flash('Only @asbarcelona.com email addresses are allowed', 'error')
            elif new_role == 'rep' and not new_grade:
                flash('Grade level is required for representatives', 'error')
            else:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO AUTHORIZED_EXECUTIVES (email, title, role, grade_level)
                        VALUES (?, ?, ?, ?)
                    """, (new_email.lower(), new_title, new_role, new_grade))
                    conn.commit()
                    flash(f'Successfully added {new_email} as {new_title}', 'success')
                except sqlite3.IntegrityError:
                    flash('This email is already authorized', 'error')
                finally:
                    conn.close()

        elif action == 'remove':
            remove_email = request.form.get('remove_email')
            current_email = current_user.email

            if remove_email.lower() == current_email.lower():
                # User is removing their own access
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()

                # Delete from authorized executives
                cursor.execute("DELETE FROM AUTHORIZED_EXECUTIVES WHERE LOWER(email) = LOWER(?)", (remove_email,))

                # Delete user account
                cursor.execute("DELETE FROM USERS WHERE LOWER(email) = LOWER(?)", (remove_email,))

                conn.commit()
                conn.close()

                # Log them out
                logout_user()
                flash('Your executive access has been removed. You have been logged out.', 'success')
                return redirect(url_for('login'))
            else:
                # Removing someone else's access
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM AUTHORIZED_EXECUTIVES WHERE LOWER(email) = LOWER(?)", (remove_email,))
                cursor.execute("DELETE FROM USERS WHERE LOWER(email) = LOWER(?)", (remove_email,))
                conn.commit()
                conn.close()
                flash(f'Successfully removed {remove_email} from authorized executives', 'success')

        return redirect(url_for('manage_executives'))

    # GET request - display the management page
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get admins (executives)
    cursor.execute("SELECT email, title, added_at FROM AUTHORIZED_EXECUTIVES WHERE role = 'admin' ORDER BY added_at")
    executives = cursor.fetchall()

    # Get reps (representatives)
    cursor.execute("SELECT email, title, added_at, grade_level FROM AUTHORIZED_EXECUTIVES WHERE role = 'rep' ORDER BY grade_level, added_at")
    reps = cursor.fetchall()

    conn.close()

    return render_template('manage_executives.html', executives=executives, reps=reps)


@app.route('/year_end_reset', methods=['GET', 'POST'])
@login_required
@admin_required
def year_end_reset():
    """Year-end reset: Remove seniors, promote students, reset all points"""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'backup':
            # Create backup
            try:
                backup_dir = os.path.join('playground', 'backups')
                os.makedirs(backup_dir, exist_ok=True)

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = os.path.join(backup_dir, f'testhouse_backup_{timestamp}.db')

                shutil.copy2(DB_PATH, backup_file)
                flash(f'Backup created successfully: {os.path.basename(backup_file)}', 'success')
            except Exception as e:
                flash(f'Error creating backup: {str(e)}', 'error')
            return redirect(url_for('year_end_reset'))

        elif action == 'restore':
            # Restore from latest backup
            try:
                backup_dir = os.path.join('playground', 'backups')
                if not os.path.exists(backup_dir):
                    flash('No backups found', 'error')
                    return redirect(url_for('year_end_reset'))

                backups = [f for f in os.listdir(backup_dir) if f.startswith('testhouse_backup_') and f.endswith('.db')]
                if not backups:
                    flash('No backups found', 'error')
                    return redirect(url_for('year_end_reset'))

                latest_backup = max(backups)
                backup_path = os.path.join(backup_dir, latest_backup)

                shutil.copy2(backup_path, DB_PATH)
                flash(f'Database restored from backup: {latest_backup}', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'Error restoring backup: {str(e)}', 'error')
            return redirect(url_for('year_end_reset'))

        elif action == 'reset':
            confirm = request.form.get('confirm')

            if confirm == 'RESET':
                # Create automatic backup before reset
                try:
                    backup_dir = os.path.join('playground', 'backups')
                    os.makedirs(backup_dir, exist_ok=True)

                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_file = os.path.join(backup_dir, f'testhouse_before_reset_{timestamp}.db')
                    shutil.copy2(DB_PATH, backup_file)
                except Exception as e:
                    flash(f'Warning: Could not create automatic backup: {str(e)}', 'error')

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()

                try:
                    # Get current year to identify seniors
                    cursor.execute("SELECT MIN(grad_year) FROM CLASS_YEARS")
                    senior_year = cursor.fetchone()[0]

                    # Count what will be affected
                    cursor.execute("SELECT COUNT(*) FROM STUDENTS WHERE class_year_id = (SELECT class_year_id FROM CLASS_YEARS WHERE grad_year = ?)", (senior_year,))
                    seniors_count = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM EVENTS")
                    events_count = cursor.fetchone()[0]

                    # Step 1: Delete all seniors
                    cursor.execute("""
                        DELETE FROM STUDENTS
                        WHERE class_year_id = (SELECT class_year_id FROM CLASS_YEARS WHERE grad_year = ?)
                    """, (senior_year,))

                    # Step 2: Delete all events and event results (resets all points)
                    cursor.execute("DELETE FROM EVENT_RESULTS")
                    cursor.execute("DELETE FROM EVENTS")

                    # Step 3: Promote all remaining students (decrease grad_year by 1)
                    cursor.execute("UPDATE CLASS_YEARS SET grad_year = grad_year - 1")

                    # Step 4: Update class names to reflect new year
                    cursor.execute("""
                        UPDATE CLASS_YEARS
                        SET class_name = CASE
                            WHEN display_order = 1 THEN 'Senior'
                            WHEN display_order = 2 THEN 'Junior'
                            WHEN display_order = 3 THEN 'Sophomore'
                            WHEN display_order = 4 THEN 'Freshman'
                        END
                    """)

                    conn.commit()

                    flash(f'Year-end reset completed! Removed {seniors_count} seniors, deleted {events_count} events, and promoted all remaining students. Backup saved automatically.', 'success')
                    return redirect(url_for('index'))

                except Exception as e:
                    conn.rollback()
                    flash(f'Error during year-end reset: {str(e)}', 'error')
                finally:
                    conn.close()
            else:
                flash('Reset cancelled. You must type "RESET" to confirm.', 'error')

    # GET request - show confirmation page with statistics
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get statistics
    cursor.execute("SELECT MIN(grad_year) FROM CLASS_YEARS")
    senior_year = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM STUDENTS WHERE class_year_id = (SELECT class_year_id FROM CLASS_YEARS WHERE grad_year = ?)", (senior_year,))
    seniors_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM STUDENTS")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM EVENTS")
    events_count = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(points_earned) FROM EVENT_RESULTS")
    total_points = cursor.fetchone()[0] or 0

    conn.close()

    stats = {
        'senior_year': senior_year,
        'seniors_count': seniors_count,
        'remaining_students': total_students - seniors_count,
        'events_count': events_count,
        'total_points': total_points
    }

    return render_template('year_end_reset.html', stats=stats)


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
@admin_required
def add_student():
    """Add new students - supports manual, CSV, and homeroom methods"""
    if request.method == 'POST':
        import_type = request.form.get('import_type', 'manual')

        if import_type == 'csv':
            # CSV Upload (from bulk_import functionality)
            if 'csv_file' not in request.files:
                flash('No file uploaded', 'error')
                return redirect(url_for('add_student'))

            file = request.files['csv_file']
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(url_for('add_student'))

            if not file.filename.endswith('.csv'):
                flash('Please upload a CSV file', 'error')
                return redirect(url_for('add_student'))

            try:
                # Read CSV file with UTF-8 encoding
                stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
                csv_reader = csv.DictReader(stream)

                # Get houses and class years for mapping
                houses_dict = {h[1].lower(): h[0] for h in get_all_houses()}
                class_years_dict = {cy[1].lower(): cy[0] for cy in get_all_class_years()}

                added_students = []
                errors = []
                line_num = 1

                for row in csv_reader:
                    line_num += 1
                    try:
                        fname = row.get('first_name', '').strip()
                        lname = row.get('last_name', '').strip()
                        email = row.get('email', '').strip()
                        house_name = row.get('house', '').strip().lower()
                        class_year_name = row.get('class_year', '').strip().lower()

                        if not all([fname, lname, email, house_name, class_year_name]):
                            errors.append(f'Line {line_num}: Missing required fields')
                            continue

                        if house_name not in houses_dict:
                            errors.append(f'Line {line_num}: Invalid house "{house_name}"')
                            continue

                        if class_year_name not in class_years_dict:
                            errors.append(f'Line {line_num}: Invalid class year "{class_year_name}"')
                            continue

                        house_id = houses_dict[house_name]
                        class_year_id = class_years_dict[class_year_name]

                        db.add_student(fname, lname, email, house_id, class_year_id)
                        added_students.append(f'{fname} {lname}')

                    except Exception as e:
                        errors.append(f'Line {line_num}: {str(e)}')

                if added_students:
                    flash(f'Successfully imported {len(added_students)} students!', 'success')

                if errors:
                    flash(f'{len(errors)} errors occurred. First few: {"; ".join(errors[:5])}', 'error')

                if added_students:
                    return redirect(url_for('students'))

            except Exception as e:
                flash(f'Error processing CSV file: {str(e)}', 'error')
                return redirect(url_for('add_student'))

        elif import_type == 'homeroom':
            # Homeroom Bulk Add
            house_id = request.form.get('house_id')
            class_year_id = request.form.get('class_year_id')
            students_text = request.form.get('students_text', '')

            if not house_id or not class_year_id:
                flash('Please select both house and class year', 'error')
                return redirect(url_for('add_student'))

            if not students_text.strip():
                flash('Please enter student names', 'error')
                return redirect(url_for('add_student'))

            lines = students_text.strip().split('\n')
            added_students = []
            errors = []

            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                if ',' in line:
                    parts = [p.strip() for p in line.split(',')]
                else:
                    parts = line.split()

                if len(parts) < 2:
                    errors.append(f'Line {i}: Need at least first and last name')
                    continue

                fname = parts[0]
                lname = ' '.join(parts[1:])
                email = f'{fname.lower()}.{lname.lower().replace(" ", "")}@asbarcelona.com'

                try:
                    db.add_student(fname, lname, email, int(house_id), int(class_year_id))
                    added_students.append(f'{fname} {lname}')
                except Exception as e:
                    errors.append(f'Line {i} ({fname} {lname}): {str(e)}')

            if added_students:
                flash(f'Successfully added {len(added_students)} students!', 'success')

            if errors:
                for error in errors[:10]:
                    flash(error, 'error')

            if added_students:
                return redirect(url_for('students'))

        else:  # manual
            student_count = int(request.form.get('student_count', 1))

            added_students = []
            errors = []

            for i in range(student_count):
                fname = request.form.get(f'fname_{i}')
                lname = request.form.get(f'lname_{i}')
                email = request.form.get(f'email_{i}')
                house_id = request.form.get(f'house_id_{i}')
                class_year_id = request.form.get(f'class_year_id_{i}')

                if not all([fname, lname, email, house_id, class_year_id]):
                    errors.append(f'Student {i + 1}: All fields are required')
                    continue

                try:
                    student_id = db.add_student(fname, lname, email, int(house_id), int(class_year_id))
                    added_students.append(f'{fname} {lname}')
                except Exception as e:
                    errors.append(f'Student {i + 1} ({fname} {lname}): {str(e)}')

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

    houses = get_all_houses()
    class_years = get_all_class_years()

    # Handle house suggestion request
    suggestion = None
    if request.args.get('get_suggestion') == '1':
        suggest_fname = request.args.get('suggest_fname', '')
        suggest_lname = request.args.get('suggest_lname', '')
        suggest_grade = request.args.get('suggest_grade', '')
        suggest_homeroom = request.args.get('suggest_homeroom', '')

        if suggest_lname and suggest_grade:
            house_id, house_name, reason = suggest_house_for_student(
                suggest_fname,
                suggest_lname,
                suggest_grade,
                suggest_homeroom if suggest_homeroom else None
            )

            if house_id:
                suggestion = {
                    'house_id': house_id,
                    'house_name': house_name,
                    'reason': reason
                }

    return render_template('add_student.html', houses=houses, class_years=class_years, suggestion=suggestion)


@app.route('/bulk-import', methods=['GET', 'POST'])
@login_required
@admin_required
def bulk_import():
    """Bulk import students via CSV or homeroom"""
    if request.method == 'POST':
        import_type = request.form.get('import_type')

        if import_type == 'csv':
            # CSV Upload
            if 'csv_file' not in request.files:
                flash('No file uploaded', 'error')
                return redirect(url_for('bulk_import'))

            file = request.files['csv_file']
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(url_for('bulk_import'))

            if not file.filename.endswith('.csv'):
                flash('Please upload a CSV file', 'error')
                return redirect(url_for('bulk_import'))

            try:
                # Read CSV file with UTF-8 encoding
                stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
                csv_reader = csv.DictReader(stream)

                # Get houses and class years for mapping
                houses = {h[1].lower(): h[0] for h in get_all_houses()}  # {name: id}
                class_years = {cy[1].lower(): cy[0] for cy in get_all_class_years()}  # {name: id}

                added_students = []
                errors = []
                line_num = 1

                for row in csv_reader:
                    line_num += 1
                    try:
                        fname = row.get('first_name', '').strip()
                        lname = row.get('last_name', '').strip()
                        email = row.get('email', '').strip()
                        house_name = row.get('house', '').strip().lower()
                        class_year_name = row.get('class_year', '').strip().lower()

                        # Validate required fields
                        if not all([fname, lname, email, house_name, class_year_name]):
                            errors.append(f'Line {line_num}: Missing required fields')
                            continue

                        # Map house and class year names to IDs
                        if house_name not in houses:
                            errors.append(f'Line {line_num}: Invalid house "{house_name}"')
                            continue

                        if class_year_name not in class_years:
                            errors.append(f'Line {line_num}: Invalid class year "{class_year_name}"')
                            continue

                        house_id = houses[house_name]
                        class_year_id = class_years[class_year_name]

                        # Add student
                        db.add_student(fname, lname, email, house_id, class_year_id)
                        added_students.append(f'{fname} {lname}')

                    except Exception as e:
                        errors.append(f'Line {line_num}: {str(e)}')

                # Show results
                if added_students:
                    flash(f'Successfully imported {len(added_students)} students!', 'success')

                if errors:
                    flash(f'{len(errors)} errors occurred. First few: {"; ".join(errors[:5])}', 'error')

                if added_students:
                    return redirect(url_for('students'))

            except Exception as e:
                flash(f'Error processing CSV file: {str(e)}', 'error')
                return redirect(url_for('bulk_import'))

        elif import_type == 'homeroom':
            # Homeroom Bulk Add
            house_id = request.form.get('house_id')
            class_year_id = request.form.get('class_year_id')
            students_text = request.form.get('students_text', '')

            if not house_id or not class_year_id:
                flash('Please select both house and class year', 'error')
                return redirect(url_for('bulk_import'))

            if not students_text.strip():
                flash('Please enter student names', 'error')
                return redirect(url_for('bulk_import'))

            # Parse student names (one per line or comma-separated)
            lines = students_text.strip().split('\n')
            added_students = []
            errors = []

            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                # Split by comma if present, otherwise by space
                if ',' in line:
                    parts = [p.strip() for p in line.split(',')]
                else:
                    parts = line.split()

                if len(parts) < 2:
                    errors.append(f'Line {i}: Need at least first and last name')
                    continue

                fname = parts[0]
                lname = ' '.join(parts[1:])  # Handle multi-part last names
                email = f'{fname.lower()}.{lname.lower().replace(" ", "")}@asbarcelona.com'

                try:
                    db.add_student(fname, lname, email, int(house_id), int(class_year_id))
                    added_students.append(f'{fname} {lname}')
                except Exception as e:
                    errors.append(f'Line {i} ({fname} {lname}): {str(e)}')

            # Show results
            if added_students:
                flash(f'Successfully added {len(added_students)} students!', 'success')

            if errors:
                for error in errors[:10]:  # Show first 10 errors
                    flash(error, 'error')

            if added_students:
                return redirect(url_for('students'))

    # GET request - show the form
    houses = get_all_houses()
    class_years = get_all_class_years()
    return render_template('bulk_import.html', houses=houses, class_years=class_years)


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
@admin_required
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
@rep_or_admin_required
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
@rep_or_admin_required
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
@admin_required
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
@admin_required
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
@admin_required
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
