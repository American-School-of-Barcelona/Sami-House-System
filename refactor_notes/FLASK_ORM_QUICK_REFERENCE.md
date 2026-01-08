# Flask-SQLAlchemy Quick Reference
## Cheat Sheet for Migration

---

## Basic Query Patterns

### Get All Records
```python
# OLD WAY (sqlite3)
cursor.execute("SELECT * FROM STUDENTS")
students = cursor.fetchall()  # Returns: [(1, 'John', 'Doe', ...), ...]

# NEW WAY (Flask-SQLAlchemy)
students = Student.query.all()  # Returns: [<Student>, <Student>, ...]
for s in students:
    print(s.fname, s.lname)  # Direct attribute access!
```

### Get One Record by ID
```python
# OLD WAY
cursor.execute("SELECT * FROM STUDENTS WHERE student_id = ?", (5,))
student = cursor.fetchone()

# NEW WAY
student = Student.query.get(5)
# OR
student = Student.query.filter_by(student_id=5).first()
```

### Filter Records
```python
# OLD WAY
cursor.execute("SELECT * FROM STUDENTS WHERE house_id = ?", (1,))
students = cursor.fetchall()

# NEW WAY
students = Student.query.filter_by(house_id=1).all()
```

### Search with LIKE
```python
# OLD WAY
cursor.execute("SELECT * FROM STUDENTS WHERE fname LIKE ?", (f"%{search}%",))

# NEW WAY
students = Student.query.filter(Student.fname.like(f"%{search}%")).all()
```

---

## Insert, Update, Delete

### Insert a Record
```python
# OLD WAY
cursor.execute("""
    INSERT INTO STUDENTS (fname, lname, email, house_id, class_year_id)
    VALUES (?, ?, ?, ?, ?)
""", (fname, lname, email, house_id, class_year_id))
conn.commit()

# NEW WAY
student = Student(
    fname=fname,
    lname=lname,
    email=email,
    house_id=house_id,
    class_year_id=class_year_id
)
db.session.add(student)
db.session.commit()
```

### Update a Record
```python
# OLD WAY
cursor.execute("""
    UPDATE STUDENTS
    SET fname = ?, lname = ?
    WHERE student_id = ?
""", (new_fname, new_lname, student_id))
conn.commit()

# NEW WAY
student = Student.query.get(student_id)
student.fname = new_fname
student.lname = new_lname
db.session.commit()
```

### Delete a Record
```python
# OLD WAY
cursor.execute("DELETE FROM STUDENTS WHERE student_id = ?", (student_id,))
conn.commit()

# NEW WAY
student = Student.query.get(student_id)
db.session.delete(student)
db.session.commit()
```

---

## Joins and Relationships

### Join Tables
```python
# OLD WAY
cursor.execute("""
    SELECT s.fname, s.lname, h.house_name, cy.class_name
    FROM STUDENTS s
    JOIN HOUSES h ON s.house_id = h.house_id
    JOIN CLASS_YEARS cy ON s.class_year_id = cy.class_year_id
""")

# NEW WAY
students = Student.query.join(House).join(ClassYear).all()
for s in students:
    print(s.fname, s.house.house_name, s.class_year.class_name)
```

### Use Relationships (No JOIN needed!)
```python
# OLD WAY - Need separate queries
cursor.execute("SELECT * FROM STUDENTS WHERE student_id = ?", (5,))
student = cursor.fetchone()
cursor.execute("SELECT * FROM HOUSES WHERE house_id = ?", (student[4],))
house = cursor.fetchone()
print(house[1])  # house_name

# NEW WAY - Automatic!
student = Student.query.get(5)
print(student.house.house_name)  # Relationship handles it!
print(student.class_year.class_name)  # No extra code!
```

---

## Aggregation Functions

### Count Records
```python
# OLD WAY
cursor.execute("SELECT COUNT(*) FROM STUDENTS WHERE house_id = ?", (1,))
count = cursor.fetchone()[0]

# NEW WAY
from sqlalchemy import func
count = Student.query.filter_by(house_id=1).count()
# OR
count = db.session.query(func.count(Student.student_id))\
    .filter_by(house_id=1).scalar()
```

### Sum / Average
```python
# OLD WAY
cursor.execute("""
    SELECT SUM(points_earned), AVG(points_earned)
    FROM EVENT_RESULTS
    WHERE house_id = ?
""", (1,))

# NEW WAY
from sqlalchemy import func
total, avg = db.session.query(
    func.sum(EventResult.points_earned),
    func.avg(EventResult.points_earned)
).filter_by(house_id=1).first()
```

### Group By
```python
# OLD WAY
cursor.execute("""
    SELECT house_id, COUNT(*)
    FROM STUDENTS
    GROUP BY house_id
""")

# NEW WAY
from sqlalchemy import func
results = db.session.query(
    Student.house_id,
    func.count(Student.student_id)
).group_by(Student.house_id).all()
```

---

## Ordering and Limiting

### Order By
```python
# OLD WAY
cursor.execute("SELECT * FROM STUDENTS ORDER BY lname, fname")

# NEW WAY
students = Student.query.order_by(Student.lname, Student.fname).all()
```

### Order Descending
```python
# OLD WAY
cursor.execute("SELECT * FROM EVENTS ORDER BY event_date DESC")

# NEW WAY
from sqlalchemy import desc
events = Event.query.order_by(desc(Event.event_date)).all()
```

### Limit Results
```python
# OLD WAY
cursor.execute("SELECT * FROM STUDENTS LIMIT 10")

# NEW WAY
students = Student.query.limit(10).all()
```

---

## Error Handling

### Rollback on Error
```python
# OLD WAY
try:
    cursor.execute("INSERT ...")
    conn.commit()
except:
    conn.rollback()

# NEW WAY
try:
    db.session.add(student)
    db.session.commit()
except:
    db.session.rollback()
    raise
```

---

## Common Flask Route Patterns

### List View
```python
# OLD WAY
@app.route('/students')
def students():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM STUDENTS")
    all_students = cursor.fetchall()
    conn.close()
    return render_template('students.html', students=all_students)

# NEW WAY
@app.route('/students')
def students():
    all_students = Student.query.all()
    return render_template('students.html', students=all_students)
```

### Detail View
```python
# OLD WAY
@app.route('/student/<int:student_id>')
def student_detail(student_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM STUDENTS WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()
    conn.close()
    return render_template('student.html', student=student)

# NEW WAY
@app.route('/student/<int:student_id>')
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)  # Auto 404 if not found!
    return render_template('student.html', student=student)
```

### Create View
```python
# OLD WAY
@app.route('/add-student', methods=['POST'])
def add_student():
    fname = request.form.get('fname')
    # ... get other fields
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO STUDENTS (fname, lname, email, house_id, class_year_id)
        VALUES (?, ?, ?, ?, ?)
    """, (fname, lname, email, house_id, class_year_id))
    conn.commit()
    conn.close()
    return redirect(url_for('students'))

# NEW WAY
@app.route('/add-student', methods=['POST'])
def add_student():
    student = Student(
        fname=request.form.get('fname'),
        lname=request.form.get('lname'),
        email=request.form.get('email'),
        house_id=request.form.get('house_id'),
        class_year_id=request.form.get('class_year_id')
    )
    db.session.add(student)
    db.session.commit()
    return redirect(url_for('students'))
```

---

## Template Changes

### Accessing Data

```html
<!-- OLD WAY: Tuple indexing -->
{% for student in students %}
    <tr>
        <td>{{ student[1] }}</td>  <!-- fname -->
        <td>{{ student[2] }}</td>  <!-- lname -->
        <td>{{ student[3] }}</td>  <!-- email -->
    </tr>
{% endfor %}

<!-- NEW WAY: Object attributes -->
{% for student in students %}
    <tr>
        <td>{{ student.fname }}</td>
        <td>{{ student.lname }}</td>
        <td>{{ student.email }}</td>
        <td>{{ student.house.house_name }}</td>  <!-- Relationship! -->
        <td>{{ student.class_year.class_name }}</td>
    </tr>
{% endfor %}
```

### Form Options

```html
<!-- OLD WAY: Tuple indexing -->
{% for house in houses %}
    <option value="{{ house[0] }}">{{ house[1] }}</option>
{% endfor %}

<!-- NEW WAY: Object attributes -->
{% for house in houses %}
    <option value="{{ house.house_id }}">{{ house.house_name }}</option>
{% endfor %}
```

---

## Flask-SQLAlchemy Specifics

### Model.query vs db.session.query()

```python
# Flask-SQLAlchemy provides Model.query shortcut
students = Student.query.all()  # Preferred!

# You can also use db.session.query() for complex queries
students = db.session.query(Student).all()  # Same thing

# Use db.session.query() when you need aggregations
from sqlalchemy import func
result = db.session.query(
    House.house_name,
    func.count(Student.student_id)
).join(Student).group_by(House.house_id).all()
```

### Automatic Session Management

```python
# Flask-SQLAlchemy manages db.session automatically!
# It's tied to the request context - no manual cleanup needed

@app.route('/add')
def add():
    student = Student(fname="John", lname="Doe")
    db.session.add(student)
    db.session.commit()
    return "Added!"
    # Session automatically cleaned up after request
```

### get_or_404()

```python
# Automatically return 404 if record doesn't exist
student = Student.query.get_or_404(student_id)
# No need for:
# if not student:
#     abort(404)
```

---

## Quick Conversion Table

| Task | Old (sqlite3) | New (Flask-SQLAlchemy) |
|------|--------------|------------------------|
| Get all | `cursor.execute("SELECT * FROM T")` | `T.query.all()` |
| Get one | `cursor.execute("... WHERE id=?", (id,))` | `T.query.get(id)` |
| Filter | `cursor.execute("... WHERE x=?", (val,))` | `T.query.filter_by(x=val).all()` |
| Insert | `cursor.execute("INSERT ...")` + `commit()` | `db.session.add(obj)` + `commit()` |
| Update | `cursor.execute("UPDATE ...")` + `commit()` | `obj.field = val` + `commit()` |
| Delete | `cursor.execute("DELETE ...")` + `commit()` | `db.session.delete(obj)` + `commit()` |
| Join | `SELECT ... JOIN ...` | `T.query.join(U)` or `obj.relationship` |
| Count | `SELECT COUNT(*)` | `T.query.count()` |

---

## Common Mistakes

### ❌ Forgetting to Commit
```python
student = Student(fname="John", lname="Doe")
db.session.add(student)
# OOPS - forgot db.session.commit()!
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
# Your Flask-Login User class conflicts with ORM User model
# Solution: Rename Flask-Login class to UserAuth

class UserAuth(UserMixin):  # Renamed!
    def __init__(self, user_id, email, role):
        self.id = user_id
        self.email = email
        self.role = role
```

---

## Setup Pattern

### app.py structure

```python
from flask import Flask
from models import db, Student, House, ClassYear  # Import from models.py

app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///playground/testhouse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database with app
db.init_app(app)

# Now use in routes
@app.route('/students')
def students():
    all_students = Student.query.all()
    return render_template('students.html', students=all_students)
```

### models.py structure

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Student(db.Model):
    __tablename__ = 'STUDENTS'
    student_id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.Text, nullable=False)
    # ... more fields
```

---

## Debugging Tips

### See Generated SQL
```python
# In app.py config:
app.config['SQLALCHEMY_ECHO'] = True  # Prints all SQL
```

### Use Flask Shell
```bash
flask shell
>>> from models import Student
>>> Student.query.all()
>>> Student.query.first().__dict__
```

### Inspect Object
```python
student = Student.query.first()
print(student.__dict__)  # See all attributes
print(student)           # Uses __repr__
```

---

## Helpful Links

- **Flask-SQLAlchemy Docs:** https://flask-sqlalchemy.palletsprojects.com/
- **SQLAlchemy Query API:** https://docs.sqlalchemy.org/en/20/orm/queryguide/
- **Your Full Guide:** See `FLASK_SQLALCHEMY_GUIDE.md`
- **Example Script:** Run `python flask_orm_example.py`
