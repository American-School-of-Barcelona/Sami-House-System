# Flask-SQLAlchemy Migration Guide
## Refactoring House Points Database to Use ORM

**Author:** For Sami
**Date:** January 2026
**Purpose:** Migrate from raw sqlite3 queries to Flask-SQLAlchemy ORM

---

## Table of Contents

1. [Why Use Flask-SQLAlchemy?](#why-use-flask-sqlalchemy)
2. [Setup and Installation](#setup-and-installation)
3. [Defining Models](#defining-models)
4. [Updating app.py](#updating-apppy)
5. [Refactoring Routes](#refactoring-routes)
6. [Updating Templates](#updating-templates)
7. [Migration Checklist](#migration-checklist)

---

## Why Use Flask-SQLAlchemy?

### Current Problems (What You Have Now)

```python
# Opening connections everywhere in app.py
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT * FROM STUDENTS WHERE house_id = ?", (house_id,))
results = cursor.fetchall()
conn.close()
# Returns raw tuples - you need to remember column order!
```

**Issues:**
- 40+ `sqlite3.connect()` calls throughout app.py
- SQL strings mixed with application logic
- Results are tuples - need to remember column positions
- Easy to forget to close connections
- Two separate helper classes to maintain
- No autocomplete for database fields

### Benefits of Flask-SQLAlchemy

```python
# Clean, Pythonic code
students = Student.query.filter_by(house_id=house_id).all()
# Returns Student objects with attributes!
for student in students:
    print(student.full_name, student.house.house_name)
```

**Benefits:**
- Write Python, not SQL
- Objects with real attributes (autocomplete works!)
- Automatic connection management
- Built-in relationship handling
- Session management tied to Flask request context
- Standard Flask pattern - matches all tutorials

---

## Setup and Installation

### Step 1: Install Flask-SQLAlchemy

Update your `requirements.txt`:
```txt
Flask==3.0.0
Flask-Login==0.6.3
Flask-Mail==0.9.1
Flask-SQLAlchemy==3.1.1
Werkzeug==3.0.1
```

Then install:
```bash
cd slrepos/Sami-House-System
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install Flask-SQLAlchemy
```

---

## Defining Models

Create a new file: `models.py` in your project root.

### `models.py` - Complete ORM Model Definitions

```python
"""
Flask-SQLAlchemy ORM Models for House Points System
Maps database tables to Python classes
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Create the database object
db = SQLAlchemy()


class ClassYear(db.Model):
    """Maps to CLASS_YEARS table"""
    __tablename__ = 'CLASS_YEARS'

    class_year_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    grad_year = db.Column(db.Integer, nullable=False, unique=True)
    class_name = db.Column(db.Text, nullable=False)
    display_order = db.Column(db.Integer, nullable=False)

    # Relationship: One ClassYear has many Students
    students = db.relationship('Student', back_populates='class_year')

    def __repr__(self):
        return f"<ClassYear(name='{self.class_name}', year={self.grad_year})>"


class House(db.Model):
    """Maps to HOUSES table"""
    __tablename__ = 'HOUSES'

    house_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    house_name = db.Column(db.Text, nullable=False, unique=True)
    logo_sq = db.Column(db.Text)
    logo_large = db.Column(db.Text)
    color = db.Column(db.Text)

    # Relationships
    students = db.relationship('Student', back_populates='house')
    event_results = db.relationship('EventResult', back_populates='house')

    def __repr__(self):
        return f"<House(name='{self.house_name}', color='{self.color}')>"


class Student(db.Model):
    """Maps to STUDENTS table"""
    __tablename__ = 'STUDENTS'

    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fname = db.Column(db.Text, nullable=False)
    lname = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text)
    house_id = db.Column(db.Integer, db.ForeignKey('HOUSES.house_id'), nullable=False)
    class_year_id = db.Column(db.Integer, db.ForeignKey('CLASS_YEARS.class_year_id'), nullable=False)

    # Relationships: Student belongs to one House and one ClassYear
    house = db.relationship('House', back_populates='students')
    class_year = db.relationship('ClassYear', back_populates='students')

    @property
    def full_name(self):
        """Convenience property for full name"""
        return f"{self.fname} {self.lname}"

    def __repr__(self):
        return f"<Student(name='{self.full_name}', house='{self.house.house_name if self.house else 'None}')>"


class Event(db.Model):
    """Maps to EVENTS table"""
    __tablename__ = 'EVENTS'

    event_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_date = db.Column(db.Text, nullable=False)  # Store as 'YYYY-MM-DD'
    event_desc = db.Column(db.Text, nullable=False)
    event_type = db.Column(db.Text)
    created_at = db.Column(db.Text, default=lambda: datetime.now().isoformat())

    # Relationship: One Event has many EventResults
    results = db.relationship('EventResult', back_populates='event', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Event(desc='{self.event_desc}', date='{self.event_date}')>"


class EventResult(db.Model):
    """Maps to EVENT_RESULTS table (junction table)"""
    __tablename__ = 'EVENT_RESULTS'

    event_id = db.Column(db.Integer, db.ForeignKey('EVENTS.event_id', ondelete='CASCADE'), primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('HOUSES.house_id'), primary_key=True)
    points_earned = db.Column(db.Integer, nullable=False, default=0)
    rank = db.Column(db.Integer, nullable=False)

    # Relationships
    event = db.relationship('Event', back_populates='results')
    house = db.relationship('House', back_populates='event_results')

    def __repr__(self):
        return f"<EventResult(event_id={self.event_id}, house_id={self.house_id}, rank={self.rank})>"


class User(db.Model):
    """Maps to USERS table"""
    __tablename__ = 'USERS'

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False, default='admin')
    created_at = db.Column(db.Text, default=lambda: datetime.now().isoformat())

    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}')>"


class AuthorizedExecutive(db.Model):
    """Maps to AUTHORIZED_EXECUTIVES table"""
    __tablename__ = 'AUTHORIZED_EXECUTIVES'

    email = db.Column(db.Text, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    added_at = db.Column(db.Text, default=lambda: datetime.now().isoformat())

    def __repr__(self):
        return f"<AuthorizedExecutive(email='{self.email}', title='{self.title}')>"
```

**Key Points:**
- Import `db` from this file in app.py: `from models import db, Student, House, ...`
- Use `db.Model` instead of `Base` - this is the Flask way
- Use `db.Column`, `db.Integer`, etc. - all through the `db` object
- Relationships still work the same way

---

## Updating app.py

### Step 1: Import Models and Initialize Database

**At the top of app.py**, replace the old imports:

```python
# OLD - REMOVE THESE:
import sqlite3
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'playground'))
from database_insert_guide import HousePointsDatabase
from analysis_queries import HousePointsAnalyzer

# NEW - ADD THESE:
from models import db, Student, House, ClassYear, Event, EventResult, User, AuthorizedExecutive
```

### Step 2: Configure and Initialize Database

**After creating the Flask app**, add:

```python
app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# NEW: Configure Flask-SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///playground/testhouse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking

# Initialize the database with the app
db.init_app(app)
```

### Step 3: Remove Old Database Objects

**DELETE these lines:**
```python
# OLD - DELETE:
DB_PATH = os.path.join('playground', 'testhouse.db')
db = HousePointsDatabase(DB_PATH)
analyzer = HousePointsAnalyzer(DB_PATH)
```

You no longer need these! Flask-SQLAlchemy handles everything.

---

## Refactoring Routes

### Example 1: Students List Page

**BEFORE (Old Way - Lines 342-392 in app.py):**

```python
@app.route('/students')
@login_required
def students():
    search_query = request.args.get('search', '').strip()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if search_query:
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
```

**AFTER (New Way with Flask-SQLAlchemy):**

```python
@app.route('/students')
@login_required
def students():
    search_query = request.args.get('search', '').strip()

    if search_query:
        # Search by name or email
        search_pattern = f"%{search_query}%"
        all_students = Student.query.join(House).join(ClassYear)\
            .filter(
                (Student.fname.like(search_pattern)) |
                (Student.lname.like(search_pattern)) |
                (Student.email.like(search_pattern))
            )\
            .order_by(House.house_name, ClassYear.display_order, Student.lname, Student.fname)\
            .all()
    else:
        # Get all students
        all_students = Student.query.join(House).join(ClassYear)\
            .order_by(House.house_name, ClassYear.display_order, Student.lname, Student.fname)\
            .all()

    return render_template('students.html', students=all_students, search_query=search_query)
```

**Improvement:** 50 lines → 18 lines! And the relationships are already loaded.

---

### Example 2: Add Student

**BEFORE (Old Way - Lines 395-445):**

```python
@app.route('/add-student', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
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
```

**AFTER (New Way):**

```python
@app.route('/add-student', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
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
                # Create and add student
                student = Student(
                    fname=fname,
                    lname=lname,
                    email=email,
                    house_id=int(house_id),
                    class_year_id=int(class_year_id)
                )
                db.session.add(student)
                db.session.commit()
                added_students.append(f'{fname} {lname}')
            except Exception as e:
                db.session.rollback()
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
    houses = House.query.order_by(House.house_name).all()
    class_years = ClassYear.query.order_by(ClassYear.display_order).all()

    return render_template('add_student.html', houses=houses, class_years=class_years)
```

**Key Changes:**
- No `db.add_student()` wrapper - create Student object directly
- Use `db.session.add()` and `db.session.commit()`
- Use `db.session.rollback()` on errors
- Query models directly: `House.query.all()`

---

### Example 3: Index/Leaderboard Page

**BEFORE (Old Way - Lines 323-339):**

```python
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
```

**AFTER (New Way):**

```python
from sqlalchemy import func, case, desc

@app.route('/')
@login_required
def index():
    """Home page - shows winning house and leaderboard"""

    # Get complete leaderboard with all stats
    leaderboard_query = db.session.query(
        House.house_name,
        House.color,
        func.coalesce(
            func.sum(
                case(
                    (Event.event_type == 'deduction', -EventResult.points_earned),
                    else_=EventResult.points_earned
                )
            ), 0
        ).label('total_points'),
        func.count(func.distinct(EventResult.event_id)).label('events_participated'),
        func.sum(case((EventResult.rank == 1, 1), else_=0)).label('wins'),
        func.sum(case((EventResult.rank == 2, 1), else_=0)).label('second_place'),
        func.sum(case((EventResult.rank == 3, 1), else_=0)).label('third_place'),
        func.sum(case((EventResult.rank == 4, 1), else_=0)).label('fourth_place')
    ).outerjoin(EventResult, House.house_id == EventResult.house_id)\
     .outerjoin(Event, EventResult.event_id == Event.event_id)\
     .group_by(House.house_id, House.house_name, House.color)\
     .order_by(desc('total_points'))\
     .all()

    # Convert to list of dicts for template
    leaderboard = []
    for rank, row in enumerate(leaderboard_query, start=1):
        leaderboard.append({
            'rank': rank,
            'house_name': row[0],
            'color': row[1],
            'total_points': row[2],
            'events_participated': row[3],
            'wins': row[4],
            'second_place': row[5],
            'third_place': row[6],
            'fourth_place': row[7]
        })

    # Winner is first in leaderboard
    winner = leaderboard[0] if leaderboard else None

    return render_template('index.html',
                         winner=winner,
                         leaderboard=leaderboard)
```

**Note:** This is more complex because it's a statistical query. For simpler queries, Flask-SQLAlchemy is much cleaner!

---

### Example 4: Helper Functions

**BEFORE (Old Way - Lines 90-137):**

```python
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
    cursor.execute("SELECT title FROM AUTHORIZED_EXECUTIVES WHERE LOWER(email) = LOWER(?)", (email,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else email


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
```

**AFTER (New Way):**

```python
def get_all_houses():
    """Get all houses from database"""
    return House.query.order_by(House.house_name).all()


def get_all_class_years():
    """Get all class years from database"""
    return ClassYear.query.order_by(ClassYear.display_order).all()


def get_executive_title(email):
    """Get the executive title for a given email from database"""
    executive = AuthorizedExecutive.query.filter(
        func.lower(AuthorizedExecutive.email) == func.lower(email)
    ).first()
    return executive.title if executive else email


def get_authorized_emails():
    """Get list of authorized executive emails from database"""
    executives = AuthorizedExecutive.query.all()
    return [exec.email for exec in executives]


def get_all_authorized_executives():
    """Get all authorized executives with their titles"""
    return AuthorizedExecutive.query.order_by(AuthorizedExecutive.added_at).all()
```

**Improvement:** 47 lines → 18 lines! Much cleaner.

---

### Example 5: Flask-Login Integration

**BEFORE (Old Way - Lines 56-71):**

```python
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
```

**AFTER (New Way):**

```python
@login_manager.user_loader
def load_user(user_id):
    """Load user from database"""
    # Special case for guest user
    if user_id == 'guest':
        return UserAuth('guest', 'Guest', 'guest')  # Renamed to avoid conflict with ORM User model

    user = User.query.get(int(user_id))
    if user:
        return UserAuth(user.user_id, user.email, user.role)
    return None
```

**Note:** You'll need to rename your Flask-Login `User` class to avoid conflict with the ORM `User` model:

```python
# Rename the Flask-Login class
class UserAuth(UserMixin):
    """User class for Flask-Login (renamed to avoid ORM conflict)"""
    def __init__(self, user_id, email, role):
        self.id = user_id
        self.email = email
        self.role = role
```

---

## Updating Templates

Templates need to change from tuple indexing to object attributes.

### students.html

**BEFORE (Tuple Indexing):**

```html
{% for student in students %}
    <tr>
        <td>{{ student[1] }}</td>  <!-- student_name -->
        <td>{{ student[2] }}</td>  <!-- email -->
        <td style="color: {{ student[4] }}">{{ student[3] }}</td>  <!-- house -->
        <td>{{ student[5] }}</td>  <!-- class_name -->
    </tr>
{% endfor %}
```

**AFTER (Object Attributes):**

```html
{% for student in students %}
    <tr>
        <td>{{ student.full_name }}</td>
        <td>{{ student.email }}</td>
        <td style="color: {{ student.house.color }}">{{ student.house.house_name }}</td>
        <td>{{ student.class_year.class_name }}</td>
    </tr>
{% endfor %}
```

### add_student.html (Forms)

**BEFORE:**

```html
{% for house in houses %}
    <option value="{{ house[0] }}">{{ house[1] }}</option>
{% endfor %}
```

**AFTER:**

```html
{% for house in houses %}
    <option value="{{ house.house_id }}">{{ house.house_name }}</option>
{% endfor %}
```

---

## Migration Checklist

### Phase 1: Setup (30 minutes)

- [ ] Install Flask-SQLAlchemy: `pip install Flask-SQLAlchemy`
- [ ] Update `requirements.txt`
- [ ] Create `models.py` with all model definitions
- [ ] Update `app.py` imports and configuration
- [ ] Test app starts: `python app.py`

### Phase 2: Migrate Helper Functions (30 minutes)

- [ ] Update `get_all_houses()`
- [ ] Update `get_all_class_years()`
- [ ] Update `get_executive_title()`
- [ ] Update `get_authorized_emails()`
- [ ] Update `get_all_authorized_executives()`
- [ ] Rename Flask-Login `User` class to `UserAuth`
- [ ] Update `load_user()` function

### Phase 3: Migrate Simple Routes (2 hours)

- [ ] Update `/students` route
- [ ] Update `/add-student` route
- [ ] Update `/edit-student/<id>` route
- [ ] Update `/events` route
- [ ] Update `/event/<id>` route
- [ ] Update `/event/<id>/delete` route
- [ ] Update `/add-event` route
- [ ] Test each route after migration

### Phase 4: Migrate Complex Routes (1-2 hours)

- [ ] Update `/` (index) route with leaderboard query
- [ ] Update `/quick-points` route
- [ ] Update `/leaderboard` route (if separate from index)
- [ ] Update `/winning-house` route
- [ ] Update authentication routes (login, register)
- [ ] Update `/manage_executives` route

### Phase 5: Update Templates (1 hour)

- [ ] Update `students.html`
- [ ] Update `add_student.html`
- [ ] Update `edit_student.html`
- [ ] Update `events.html`
- [ ] Update `event_details.html`
- [ ] Update `add_event.html`
- [ ] Update `index.html`
- [ ] Update `leaderboard.html`
- [ ] Update `winning_house.html`

### Phase 6: Testing & Cleanup (1 hour)

- [ ] Test all functionality in browser
- [ ] Verify leaderboard calculates correctly
- [ ] Test add/edit/delete operations
- [ ] Test search functionality
- [ ] Test authentication flows
- [ ] Remove old helper files (keep as backup first!)
  - [ ] Move `playground/database_insert_guide.py` to backup folder
  - [ ] Move `playground/analysis_queries.py` to backup folder
- [ ] Update documentation

**Total Time:** ~6-8 hours

---

## Quick Reference

### Basic Patterns

```python
# Query all
students = Student.query.all()

# Query with filter
students = Student.query.filter_by(house_id=1).all()

# Query one
student = Student.query.get(5)  # By primary key
student = Student.query.filter_by(email='test@example.com').first()

# Search
students = Student.query.filter(Student.fname.like('%John%')).all()

# Join
students = Student.query.join(House).filter(House.house_name == 'Athena').all()

# Add record
student = Student(fname='John', lname='Doe', email='jdoe@test.com', house_id=1, class_year_id=2)
db.session.add(student)
db.session.commit()

# Update record
student = Student.query.get(5)
student.email = 'newemail@test.com'
db.session.commit()

# Delete record
student = Student.query.get(5)
db.session.delete(student)
db.session.commit()

# Rollback on error
try:
    db.session.add(student)
    db.session.commit()
except:
    db.session.rollback()
    raise
```

### Relationships

```python
# Access related objects (automatic joins!)
student = Student.query.get(5)
print(student.house.house_name)        # No extra query needed if loaded!
print(student.class_year.class_name)

# Get all students in a house
house = House.query.first()
for student in house.students:  # Uses relationship
    print(student.full_name)
```

---

## Common Pitfalls

### ❌ Forgetting to Commit
```python
student = Student(fname="John", lname="Doe")
db.session.add(student)
# FORGOT: db.session.commit()
```

### ❌ Not Rolling Back on Error
```python
try:
    db.session.add(student)
    db.session.commit()
except:
    # FORGOT: db.session.rollback()
    raise
```

### ❌ Using Tuple Index in Templates
```html
<!-- OLD - WRONG: -->
{{ student[0] }}

<!-- NEW - CORRECT: -->
{{ student.fname }}
```

### ❌ Model Name Conflicts
```python
# Flask-Login User class conflicts with ORM User model
# Solution: Rename Flask-Login class to UserAuth
```

---

## Benefits You'll See

**Before Migration:**
- 774 lines in app.py
- 2 helper files (675 lines total)
- 40+ manual database connections
- SQL strings everywhere

**After Migration:**
- ~500 lines in app.py (35% reduction!)
- No helper files needed
- Zero manual connections
- Pythonic, readable code

---

## Need Help?

If stuck:
1. Check Flask-SQLAlchemy docs: https://flask-sqlalchemy.palletsprojects.com/
2. Print objects: `print(student.__dict__)`
3. Enable SQL logging: `app.config['SQLALCHEMY_ECHO'] = True`
4. Test queries in Flask shell: `flask shell`

Good luck! The code will be much cleaner when you're done.
