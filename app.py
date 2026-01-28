"""
Flask Web Application for House Points System
No JavaScript - Pure HTML and Flask
Using SQLAlchemy ORM instead of raw SQL queries

Run with:
    python app.py
Then visit: http://localhost:5000
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import shutil
import csv
import io
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# Database path - use absolute path for PythonAnywhere compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'playground', 'testhouse.db')

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import and initialize SQLAlchemy models
from models import db, House, ClassYear, Student, Event, EventResult, User, AuthorizedExecutive
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'


# ============================================
# GUEST USER CLASS FOR FLASK-LOGIN
# ============================================

class GuestUser:
    """Guest user class for Flask-Login (not stored in database)"""
    def __init__(self):
        self.id = 'guest'
        self.email = 'Guest'
        self.role = 'guest'

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return 'guest'

    @property
    def username(self):
        return self.email


@login_manager.user_loader
def load_user(user_id):
    """Load user from database using ORM"""
    # Special case for guest user
    if user_id == 'guest':
        return GuestUser()

    # Use SQLAlchemy ORM to get user
    user = User.get_by_id(user_id)
    return user


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
    """Get all houses from database using ORM"""
    houses = House.query.order_by(House.house_name).all()
    return [(h.house_id, h.house_name, h.color) for h in houses]


def get_all_class_years():
    """Get all class years from database using ORM"""
    class_years = ClassYear.query.order_by(ClassYear.display_order).all()
    return [(cy.class_year_id, cy.class_name, cy.grad_year) for cy in class_years]


def get_executive_title(email):
    """Get the executive title for a given email from database using ORM"""
    executive = AuthorizedExecutive.get_by_email(email)
    return executive.title if executive else email


def get_executive_role(email):
    """Get the role for a given email from database using ORM"""
    executive = AuthorizedExecutive.get_by_email(email)
    return executive.role if executive else 'admin'  # Default to admin for backwards compatibility


def suggest_house_for_student(first_name, last_name, grade, homeroom=None):
    """
    Suggest the best house for a new student based on:
    1. 9th graders -> their homeroom's house (9A=Artemis, 9B=Athena, 9C=Poseidon, 9D=Apollo)
    2. Sibling matching -> same house as existing student with same last name
    3. Balance -> house with fewest students

    Returns: (suggested_house_id, suggested_house_name, reason, siblings_list)
    siblings_list is a list of tuples: [(first_name, house_name, grade), ...]
    """
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
            # Get the house using ORM
            house = House.query.filter_by(house_name=house_name).first()

            if house:
                return (house.house_id, house_name, f"9th grader in homeroom {homeroom_upper} - assigned to {house_name}", [])

    # PRIORITY 2: Check for siblings (same last name) - get ALL siblings using ORM
    siblings_query = db.session.query(
        Student.fname,
        House.house_name,
        ClassYear.class_name,
        Student.house_id
    ).join(House, Student.house_id == House.house_id
    ).join(ClassYear, Student.class_year_id == ClassYear.class_year_id
    ).filter(
        db.func.lower(Student.lname) == last_name.lower(),
        Student.house_id.isnot(None)
    ).order_by(ClassYear.grad_year.desc(), Student.fname).all()

    if siblings_query:
        # Format siblings list for display
        siblings_list = [(s.fname, s.house_name, s.class_name) for s in siblings_query]

        # Check if siblings are in multiple houses
        unique_houses = {}  # house_id -> (house_name, count, [sibling_names])
        for s in siblings_query:
            hid = s.house_id
            hname = s.house_name
            fname = s.fname
            if hid not in unique_houses:
                unique_houses[hid] = (hname, 0, [])
            house_info = unique_houses[hid]
            unique_houses[hid] = (house_info[0], house_info[1] + 1, house_info[2] + [fname])

        if len(unique_houses) == 1:
            # All siblings in same house - suggest that house
            first_sibling = siblings_query[0]
            house_id = first_sibling.house_id
            house_name = first_sibling.house_name

            if len(siblings_query) == 1:
                reason = f"Sibling match - {first_sibling.fname} {last_name} is in {house_name}"
            else:
                sibling_names = ", ".join([s.fname for s in siblings_query])
                reason = f"Sibling match - {len(siblings_query)} siblings found ({sibling_names}) in {house_name}"

            return (house_id, house_name, reason, siblings_list)
        else:
            # Siblings split across multiple houses - suggest both with counts
            house_options = []
            for hid, (hname, count, names) in unique_houses.items():
                house_options.append((hid, hname, count, names))

            # Sort by count (descending) - suggest the house with most siblings first
            house_options.sort(key=lambda x: x[2], reverse=True)

            # Check if there's a tie (equal number of siblings in top houses)
            top_sibling_count = house_options[0][2]
            tied_houses = [h for h in house_options if h[2] == top_sibling_count]

            if len(tied_houses) > 1:
                # Tie detected - use total house population as tiebreaker
                house_totals = {}
                for hid, hname, sib_count, names in tied_houses:
                    total_count = Student.query.filter_by(house_id=hid).count()
                    house_totals[hid] = (hname, sib_count, names, total_count)

                # Sort tied houses by total population (ascending - prefer smaller house)
                tied_houses_with_totals = [(hid, hname, sib_count, names, house_totals[hid][3])
                                           for hid, hname, sib_count, names in tied_houses]
                tied_houses_with_totals.sort(key=lambda x: x[4])  # Sort by total count

                # Primary suggestion is the tied house with fewest total students
                primary_house_id = tied_houses_with_totals[0][0]
                primary_house_name = tied_houses_with_totals[0][1]
                primary_total = tied_houses_with_totals[0][4]

                # Build reason message showing both houses with totals
                house_breakdown = []
                for hid, hname, count, names in house_options:
                    house_breakdown.append(f"{hname} ({count}: {', '.join(names)})")

                reason = f"Siblings split across {len(unique_houses)} houses - {' | '.join(house_breakdown)}. Tied at {top_sibling_count} sibling(s) each, suggesting {primary_house_name} (fewer total students: {primary_total})"
            else:
                # No tie - suggest house with most siblings
                primary_house_id = house_options[0][0]
                primary_house_name = house_options[0][1]

                # Build reason message showing both houses
                house_breakdown = []
                for hid, hname, count, names in house_options:
                    house_breakdown.append(f"{hname} ({count}: {', '.join(names)})")

                reason = f"Siblings split across {len(unique_houses)} houses - {' | '.join(house_breakdown)}. Suggesting {primary_house_name} (most siblings)"

            return (primary_house_id, primary_house_name, reason, siblings_list)

    # PRIORITY 3: Balance houses - assign to house with fewest students using ORM
    house_counts = db.session.query(
        Student.house_id,
        House.house_name,
        db.func.count(Student.student_id).label('count')
    ).join(House, Student.house_id == House.house_id
    ).filter(Student.house_id.isnot(None)
    ).group_by(Student.house_id, House.house_name
    ).order_by(db.func.count(Student.student_id).asc()).all()

    if house_counts:
        smallest = house_counts[0]
        return (smallest.house_id, smallest.house_name, f"Balanced distribution - {smallest.house_name} has fewest students ({smallest.count})", [])

    # Fallback: if no students exist yet, return None
    return (None, None, "No existing students to base assignment on", [])


def get_authorized_emails():
    """Get list of authorized executive emails from database using ORM"""
    return AuthorizedExecutive.get_all_emails()


def get_all_authorized_executives():
    """Get all authorized executives with their titles using ORM"""
    executives = AuthorizedExecutive.query.order_by(AuthorizedExecutive.added_at).all()
    return [(e.email, e.title, e.added_at) for e in executives]


# ============================================
# LEADERBOARD & ANALYSIS HELPER FUNCTIONS (ORM)
# ============================================

def get_house_points():
    """
    Get total points for each house, accounting for deductions.
    Deduction events have event_type='deduction' and should be subtracted.
    Returns: dict of {house_id: (house_name, total_points, color)}
    """
    # Get all houses first
    houses = House.query.all()
    house_dict = {h.house_id: (h.house_name, 0, h.color) for h in houses}

    # Calculate points for each house
    # Join EventResult with Event to check event_type
    results = db.session.query(
        EventResult.house_id,
        Event.event_type,
        db.func.sum(EventResult.points_earned).label('points')
    ).join(Event, EventResult.event_id == Event.event_id
    ).group_by(EventResult.house_id, Event.event_type).all()

    # Process results - subtract deductions, add everything else
    for result in results:
        house_id = result.house_id
        if house_id in house_dict:
            house_name, current_points, color = house_dict[house_id]
            if result.event_type == 'deduction':
                current_points -= result.points
            else:
                current_points += result.points
            house_dict[house_id] = (house_name, current_points, color)

    return house_dict


def get_winning_house():
    """
    Get the house with the most points.
    Returns: tuple (house_name, color, points, events, wins) or None if no points
    Template expects: winner[0]=name, winner[2]=points, winner[3]=events, winner[4]=wins
    """
    house_points = get_house_points()

    if not house_points:
        return None

    # Find house with maximum points
    winner_id = max(house_points.keys(), key=lambda x: house_points[x][1])
    house_name, total_points, color = house_points[winner_id]

    # Get event stats for winning house
    results = db.session.query(
        EventResult.rank,
        db.func.count(EventResult.event_id).label('count')
    ).filter(EventResult.house_id == winner_id
    ).group_by(EventResult.rank).all()

    events = sum(r.count for r in results)
    wins = sum(r.count for r in results if r.rank == 1)

    # Return tuple for template: (house_name, color, points, events, wins)
    return (house_name, color, total_points, events, wins)


def get_complete_leaderboard():
    """
    Get all houses ranked by total points.
    Returns: list of tuples (rank, house_name, color, points, events, wins, second, third, fourth)
    """
    house_points = get_house_points()

    # Get rank counts for each house (wins, second, third, fourth place finishes)
    rank_counts = {}
    for house_id in house_points.keys():
        rank_counts[house_id] = {1: 0, 2: 0, 3: 0, 4: 0, 'events': 0}

    # Query event results to count ranks
    results = db.session.query(
        EventResult.house_id,
        EventResult.rank,
        db.func.count(EventResult.event_id).label('count')
    ).group_by(EventResult.house_id, EventResult.rank).all()

    for result in results:
        if result.house_id in rank_counts:
            if result.rank in rank_counts[result.house_id]:
                rank_counts[result.house_id][result.rank] = result.count
            rank_counts[result.house_id]['events'] += result.count

    # Sort by points descending
    sorted_houses = sorted(house_points.items(), key=lambda x: x[1][1], reverse=True)

    leaderboard = []
    for rank, (house_id, (house_name, total_points, color)) in enumerate(sorted_houses, 1):
        counts = rank_counts.get(house_id, {1: 0, 2: 0, 3: 0, 4: 0, 'events': 0})
        # Return tuple: (rank, house_name, color, points, events, wins, second, third, fourth)
        leaderboard.append((
            rank,
            house_name,
            color,
            total_points,
            counts['events'],
            counts[1],  # wins (1st place)
            counts[2],  # second
            counts[3],  # third
            counts[4]   # fourth
        ))

    return leaderboard


def get_standings_with_points_ahead():
    """
    Get leaderboard with points difference from leader.
    Returns: list of tuples (rank, house_name, color, points, events, wins, second, third, fourth, points_behind)
    """
    leaderboard = get_complete_leaderboard()

    if not leaderboard:
        return []

    # Leaderboard format: (rank, house_name, color, points, events, wins, second, third, fourth)
    leader_points = leaderboard[0][3]  # points is at index 3

    standings = []
    for entry in leaderboard:
        # Add points_behind as 10th element
        points_behind = leader_points - entry[3]
        standings.append(entry + (points_behind,))

    return standings


def get_students_by_house_standing():
    """
    Get students grouped by house ranking (1st place house, 2nd place house, etc.)
    Returns: dict where keys are ranks (1, 2, 3, 4) and values are lists of student info
    """
    leaderboard = get_complete_leaderboard()

    students_by_standing = {}

    # Leaderboard format: (rank, house_name, color, points, events, wins, second, third, fourth)
    for entry in leaderboard:
        rank = entry[0]
        house_name = entry[1]
        color = entry[2]
        total_points = entry[3]

        # Get house by name to find house_id
        house = House.query.filter_by(house_name=house_name).first()
        if not house:
            continue

        # Get students in this house using ORM
        students = db.session.query(
            Student.student_id,
            Student.fname,
            Student.lname,
            Student.email,
            ClassYear.class_name
        ).join(ClassYear, Student.class_year_id == ClassYear.class_year_id
        ).filter(Student.house_id == house.house_id
        ).order_by(Student.lname, Student.fname).all()

        students_by_standing[rank] = {
            'house_name': house_name,
            'house_color': color,
            'total_points': total_points,
            'students': [(s.student_id, s.fname, s.lname, s.email, s.class_name) for s in students]
        }

    return students_by_standing


def get_students_in_winning_house():
    """
    Get all students in the winning house.
    Returns: list of tuples (student_name, email, house_name, color, class_name, grad_year, points)
    Template expects this format for winning_students
    """
    winner = get_winning_house()

    if not winner:
        return []

    # Winner is tuple: (house_name, color, points, events, wins)
    house_name = winner[0]
    color = winner[1]
    points = winner[2]

    house = House.query.filter_by(house_name=house_name).first()
    if not house:
        return []

    students = db.session.query(
        Student.fname,
        Student.lname,
        Student.email,
        ClassYear.class_name,
        ClassYear.grad_year
    ).join(ClassYear, Student.class_year_id == ClassYear.class_year_id
    ).filter(Student.house_id == house.house_id
    ).order_by(Student.lname, Student.fname).all()

    # Return format: (student_name, email, house_name, color, class_name, grad_year, points)
    return [(f"{s.fname} {s.lname}", s.email, house_name, color, s.class_name, s.grad_year, points) for s in students]


def get_winning_house_students_by_grade():
    """
    Get students in the winning house grouped by grade level.
    Returns: list of tuples (class_name, grad_year, count, students_string)
    Template expects this format for iteration
    """
    winner = get_winning_house()

    if not winner:
        return []

    # Winner is tuple: (house_name, color, points, events, wins)
    house_name = winner[0]
    house = House.query.filter_by(house_name=house_name).first()
    if not house:
        return []

    # Get all class years
    class_years = ClassYear.query.order_by(ClassYear.display_order).all()

    students_by_grade = []

    for cy in class_years:
        students = db.session.query(
            Student.fname,
            Student.lname
        ).filter(
            Student.house_id == house.house_id,
            Student.class_year_id == cy.class_year_id
        ).order_by(Student.lname, Student.fname).all()

        count = len(students)
        students_string = ", ".join([f"{s.fname} {s.lname}" for s in students]) if students else "None"

        # Return format: (class_name, grad_year, count, students_string)
        students_by_grade.append((cy.class_name, cy.grad_year, count, students_string))

    return students_by_grade


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

        # Get user from database using ORM
        user = User.get_by_email(email)

        # Check if user exists and password is correct
        if user and check_password_hash(user.password_hash, password):
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
    guest_user = GuestUser()
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

        # Get authorized emails from database using ORM
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
            # Check if email already exists using ORM
            existing_user = User.get_by_email(email)

            if existing_user:
                flash('An account with this email already exists.', 'error')
            else:
                # Create new user with correct role from database using ORM
                user_role = get_executive_role(email)
                password_hash = generate_password_hash(password)
                new_user = User(
                    email=email,
                    password_hash=password_hash,
                    role=user_role
                )
                db.session.add(new_user)
                db.session.commit()

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
    """Manage authorized executive emails and titles using ORM"""
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
                # Check if already exists
                existing = AuthorizedExecutive.get_by_email(new_email)
                if existing:
                    flash('This email is already authorized', 'error')
                else:
                    new_exec = AuthorizedExecutive(
                        email=new_email.lower(),
                        title=new_title,
                        role=new_role,
                        grade_level=new_grade
                    )
                    db.session.add(new_exec)
                    db.session.commit()
                    flash(f'Successfully added {new_email} as {new_title}', 'success')

        elif action == 'remove':
            remove_email = request.form.get('remove_email')
            current_email = current_user.email

            # Delete from authorized executives
            exec_to_remove = AuthorizedExecutive.get_by_email(remove_email)
            if exec_to_remove:
                db.session.delete(exec_to_remove)

            # Delete user account
            user_to_remove = User.get_by_email(remove_email)
            if user_to_remove:
                db.session.delete(user_to_remove)

            db.session.commit()

            if remove_email.lower() == current_email.lower():
                # User is removing their own access - log them out
                logout_user()
                flash('Your executive access has been removed. You have been logged out.', 'success')
                return redirect(url_for('login'))
            else:
                flash(f'Successfully removed {remove_email} from authorized executives', 'success')

        return redirect(url_for('manage_executives'))

    # GET request - display the management page using ORM
    executives = AuthorizedExecutive.query.filter_by(role='admin').order_by(AuthorizedExecutive.added_at).all()
    # Convert datetime to string for template compatibility
    executives = [(e.email, e.title, e.added_at.isoformat() if e.added_at else None) for e in executives]

    reps = AuthorizedExecutive.query.filter_by(role='rep').order_by(AuthorizedExecutive.grade_level, AuthorizedExecutive.added_at).all()
    reps = [(r.email, r.title, r.added_at.isoformat() if r.added_at else None, r.grade_level) for r in reps]

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
                    backup_dir = os.path.join(BASE_DIR, 'playground', 'backups')
                    os.makedirs(backup_dir, exist_ok=True)

                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_file = os.path.join(backup_dir, f'testhouse_before_reset_{timestamp}.db')
                    shutil.copy2(DB_PATH, backup_file)
                except Exception as e:
                    flash(f'Warning: Could not create automatic backup: {str(e)}', 'error')

                try:
                    # Get current year to identify seniors using ORM
                    senior_class = ClassYear.query.order_by(ClassYear.grad_year.asc()).first()
                    senior_year = senior_class.grad_year if senior_class else None

                    # Count what will be affected
                    seniors_count = Student.query.filter_by(class_year_id=senior_class.class_year_id).count() if senior_class else 0
                    events_count = Event.query.count()

                    # Step 1: Delete all seniors
                    if senior_class:
                        Student.query.filter_by(class_year_id=senior_class.class_year_id).delete()

                    # Step 2: Delete all events and event results (resets all points)
                    EventResult.query.delete()
                    Event.query.delete()

                    # Step 3: Promote all remaining students (decrease grad_year by 1)
                    for cy in ClassYear.query.all():
                        cy.grad_year = cy.grad_year - 1

                    # Step 4: Update class names to reflect new year
                    class_name_map = {1: 'Senior', 2: 'Junior', 3: 'Sophomore', 4: 'Freshman'}
                    for cy in ClassYear.query.all():
                        if cy.display_order in class_name_map:
                            cy.class_name = class_name_map[cy.display_order]

                    db.session.commit()

                    flash(f'Year-end reset completed! Removed {seniors_count} seniors, deleted {events_count} events, and promoted all remaining students. Backup saved automatically.', 'success')
                    return redirect(url_for('index'))

                except Exception as e:
                    db.session.rollback()
                    flash(f'Error during year-end reset: {str(e)}', 'error')
            else:
                flash('Reset cancelled. You must type "RESET" to confirm.', 'error')

    # GET request - show confirmation page with statistics using ORM
    senior_class = ClassYear.query.order_by(ClassYear.grad_year.asc()).first()
    senior_year = senior_class.grad_year if senior_class else None
    seniors_count = Student.query.filter_by(class_year_id=senior_class.class_year_id).count() if senior_class else 0
    total_students = Student.query.count()
    events_count = Event.query.count()
    total_points = db.session.query(db.func.sum(EventResult.points_earned)).scalar() or 0

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
    # Get winning house using ORM helper
    winner = get_winning_house()

    # Get complete leaderboard using ORM helper
    leaderboard = get_complete_leaderboard()

    # Get house standings with points ahead using ORM helper
    standings = get_standings_with_points_ahead()

    return render_template('index.html',
                         winner=winner,
                         leaderboard=leaderboard,
                         standings=standings)


@app.route('/students')
@login_required
def students():
    """View all students with search functionality using ORM"""
    search_query = request.args.get('search', '').strip()

    # Build query using ORM
    query = db.session.query(
        Student.student_id,
        (Student.fname + ' ' + Student.lname).label('student_name'),
        Student.email,
        House.house_name,
        House.color,
        ClassYear.class_name
    ).join(House, Student.house_id == House.house_id
    ).join(ClassYear, Student.class_year_id == ClassYear.class_year_id)

    if search_query:
        # Search by name or email
        search_pattern = f"%{search_query}%"
        query = query.filter(
            db.or_(
                (Student.fname + ' ' + Student.lname).ilike(search_pattern),
                Student.email.ilike(search_pattern),
                Student.fname.ilike(search_pattern),
                Student.lname.ilike(search_pattern)
            )
        )

    # Order results
    query = query.order_by(House.house_name, ClassYear.display_order, Student.lname, Student.fname)

    all_students = [(s.student_id, s.student_name, s.email, s.house_name, s.color, s.class_name)
                    for s in query.all()]

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
            house_id, house_name, reason, siblings_list = suggest_house_for_student(
                suggest_fname,
                suggest_lname,
                suggest_grade,
                suggest_homeroom if suggest_homeroom else None
            )

            if house_id:
                suggestion = {
                    'house_id': house_id,
                    'house_name': house_name,
                    'reason': reason,
                    'siblings': siblings_list
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
    """View all events using ORM"""
    # Get all events with their results count
    all_events_query = db.session.query(
        Event.event_id,
        Event.event_date,
        Event.event_desc,
        Event.event_type,
        db.func.count(EventResult.house_id).label('houses_participated')
    ).outerjoin(EventResult, Event.event_id == EventResult.event_id
    ).group_by(Event.event_id
    ).order_by(Event.event_date.desc()).all()

    all_events = [(e.event_id, e.event_date, e.event_desc, e.event_type, e.houses_participated)
                  for e in all_events_query]

    return render_template('events.html', events=all_events)


@app.route('/event/<int:event_id>')
@login_required
def event_details(event_id):
    """View details of a specific event using ORM"""
    # Get event info
    event_obj = Event.query.get(event_id)
    if not event_obj:
        flash('Event not found', 'error')
        return redirect(url_for('events'))

    # Hide quick_points and deduction events from guests
    if current_user.role == 'guest' and event_obj.event_type in ['quick_points', 'deduction']:
        flash('You do not have permission to view this event', 'error')
        return redirect(url_for('events'))

    event = (event_obj.event_id, event_obj.event_date, event_obj.event_desc, event_obj.event_type)

    # Get results for this event
    results_query = db.session.query(
        House.house_name,
        House.color,
        EventResult.rank,
        EventResult.points_earned
    ).join(House, EventResult.house_id == House.house_id
    ).filter(EventResult.event_id == event_id
    ).order_by(EventResult.rank).all()

    results = [(r.house_name, r.color, r.rank, r.points_earned) for r in results_query]

    return render_template('event_details.html', event=event, results=results)


@app.route('/event/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_event(event_id):
    """Delete an event and all its results using ORM"""
    try:
        # Get event for the flash message
        event = Event.query.get(event_id)
        event_name = event.event_desc if event else "Event"

        if event:
            # Delete event results first (cascade should handle this but being explicit)
            EventResult.query.filter_by(event_id=event_id).delete()

            # Delete the event
            db.session.delete(event)
            db.session.commit()

            flash(f'Successfully deleted event: {event_name}', 'success')
        else:
            flash('Event not found', 'error')
    except Exception as e:
        db.session.rollback()
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
    """Quick points input without creating an event using ORM"""
    if request.method == 'POST':
        # Get houses
        houses = get_all_houses()
        points_awarded = []

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

                        # Create new Event using ORM
                        new_event = Event(
                            event_date=event_date,
                            event_desc=event_name,
                            event_type=event_type
                        )
                        db.session.add(new_event)
                        db.session.flush()  # Get the event_id

                        # Create EventResult using ORM
                        new_result = EventResult(
                            event_id=new_event.event_id,
                            house_id=house_id,
                            points_earned=stored_points,
                            rank=1
                        )
                        db.session.add(new_result)

                        # Format the message with + or - prefix
                        sign = '+' if points_value > 0 else ''
                        points_awarded.append(f"{house_name}: {sign}{points_value} points")

            db.session.commit()

            if points_awarded:
                flash(f"Successfully applied points! {', '.join(points_awarded)}", 'success')
            else:
                flash('No points were applied. Please enter points for at least one house.', 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'Error awarding points: {str(e)}', 'error')

        return redirect(url_for('index'))

    # GET request - show form
    houses = get_all_houses()
    return render_template('quick_points.html', houses=houses)


@app.route('/edit-student/<int:student_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_student(student_id):
    """Edit an existing student using ORM"""
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
                # Update student in database using ORM
                student = Student.query.get(student_id)
                if student:
                    student.fname = fname
                    student.lname = lname
                    student.email = email
                    student.house_id = int(house_id)
                    student.class_year_id = int(class_year_id)
                    db.session.commit()

                    flash(f'Successfully updated {fname} {lname}!', 'success')
                    return redirect(url_for('students'))
                else:
                    flash('Student not found!', 'error')
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating student: {str(e)}', 'error')

    # GET request - show form with current data using ORM
    student_obj = Student.query.get(student_id)

    if not student_obj:
        flash('Student not found!', 'error')
        return redirect(url_for('students'))

    # Convert to tuple format for template compatibility
    student = (student_obj.student_id, student_obj.fname, student_obj.lname,
               student_obj.email, student_obj.house_id, student_obj.class_year_id)

    # Get houses and class years for the form
    houses = get_all_houses()
    class_years = get_all_class_years()

    return render_template('edit_student.html', student=student, houses=houses, class_years=class_years)


@app.route('/leaderboard')
@login_required
@admin_required
def leaderboard():
    """Full leaderboard page using ORM"""
    # Get complete leaderboard using ORM helper
    leaderboard_data = get_complete_leaderboard()

    # Get students by house standing using ORM helper
    students_by_standing = get_students_by_house_standing()

    return render_template('leaderboard.html',
                         leaderboard=leaderboard_data,
                         students_by_standing=students_by_standing)


@app.route('/winning-house')
@login_required
@admin_required
def winning_house():
    """Detailed winning house page using ORM"""
    # Get winning house using ORM helper
    winner = get_winning_house()

    # Get students in winning house using ORM helper
    winning_students = get_students_in_winning_house()

    # Get winning house students grouped by grade using ORM helper
    students_by_grade = get_winning_house_students_by_grade()

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
