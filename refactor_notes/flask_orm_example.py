"""
Flask-SQLAlchemy ORM Quick Start Example
Run this to see Flask-SQLAlchemy in action with your existing database!

Before running:
    pip install Flask-SQLAlchemy

Then run:
    python flask_orm_example.py
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///playground/testhouse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create database object
db = SQLAlchemy(app)


# Define simplified models
class House(db.Model):
    __tablename__ = 'HOUSES'
    house_id = db.Column(db.Integer, primary_key=True)
    house_name = db.Column(db.Text, nullable=False)
    color = db.Column(db.Text)
    students = db.relationship('Student', back_populates='house')

    def __repr__(self):
        return f"<House(name='{self.house_name}', color='{self.color}')>"


class ClassYear(db.Model):
    __tablename__ = 'CLASS_YEARS'
    class_year_id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.Text, nullable=False)
    grad_year = db.Column(db.Integer)
    students = db.relationship('Student', back_populates='class_year')

    def __repr__(self):
        return f"<ClassYear(name='{self.class_name}', year={self.grad_year})>"


class Student(db.Model):
    __tablename__ = 'STUDENTS'
    student_id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.Text, nullable=False)
    lname = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text)
    house_id = db.Column(db.Integer, db.ForeignKey('HOUSES.house_id'))
    class_year_id = db.Column(db.Integer, db.ForeignKey('CLASS_YEARS.class_year_id'))

    house = db.relationship('House', back_populates='students')
    class_year = db.relationship('ClassYear', back_populates='students')

    @property
    def full_name(self):
        return f"{self.fname} {self.lname}"

    def __repr__(self):
        return f"<Student(name='{self.full_name}')>"


def main():
    """Demonstrate Flask-SQLAlchemy capabilities"""

    print("\n" + "="*70)
    print("Flask-SQLAlchemy ORM Demo - House Points Database")
    print("="*70)

    with app.app_context():
        # ========================================
        # Example 1: Get all houses
        # ========================================
        print("\n📚 Example 1: Get All Houses (No Session Management!)")
        print("-" * 70)

        houses = House.query.all()
        for house in houses:
            print(f"  {house.house_name:15} (Color: {house.color})")

        # ========================================
        # Example 2: Get students with relationships
        # ========================================
        print("\n📚 Example 2: Get First 5 Students (with House & Class)")
        print("-" * 70)

        students = Student.query.limit(5).all()
        for student in students:
            print(f"  {student.full_name:20} │ {student.house.house_name:12} │ {student.class_year.class_name}")

        # ========================================
        # Example 3: Filter students by house
        # ========================================
        print("\n📚 Example 3: Students in First House (using filter_by)")
        print("-" * 70)

        first_house = House.query.first()
        print(f"House: {first_house.house_name}\n")

        students_in_house = Student.query.filter_by(house_id=first_house.house_id).limit(5).all()

        for student in students_in_house:
            print(f"  - {student.full_name} ({student.email})")

        # ========================================
        # Example 4: Use relationships (backward navigation)
        # ========================================
        print("\n📚 Example 4: Navigate Relationships (Both Directions)")
        print("-" * 70)

        # Forward: Student → House
        one_student = Student.query.first()
        print(f"Student: {one_student.full_name}")
        print(f"  → House: {one_student.house.house_name} ({one_student.house.color})")
        print(f"  → Class: {one_student.class_year.class_name} (Grad {one_student.class_year.grad_year})")

        # Backward: House → Students
        print(f"\nHouse: {first_house.house_name}")
        print(f"  → Has {len(first_house.students)} students")

        # ========================================
        # Example 5: Count students per house
        # ========================================
        print("\n📚 Example 5: Count Students Per House")
        print("-" * 70)

        from sqlalchemy import func

        house_counts = db.session.query(
            House.house_name,
            func.count(Student.student_id).label('student_count')
        ).outerjoin(Student, House.house_id == Student.house_id)\
         .group_by(House.house_id, House.house_name)\
         .all()

        for house_name, count in house_counts:
            print(f"  {house_name:15} has {count} students")

        # ========================================
        # Example 6: Search students by name
        # ========================================
        print("\n📚 Example 6: Search Students (name contains 'a')")
        print("-" * 70)

        search_results = Student.query.filter(Student.fname.like('%a%')).limit(5).all()

        for student in search_results:
            print(f"  {student.full_name} - {student.house.house_name}")

        # ========================================
        # Example 7: Join and filter
        # ========================================
        print("\n📚 Example 7: Complex Query (Join + Filter + Order)")
        print("-" * 70)

        # Get students from a specific house, ordered by class year
        results = Student.query.join(House).join(ClassYear)\
            .filter(House.house_name.like('A%'))\
            .order_by(ClassYear.display_order, Student.lname)\
            .limit(5)\
            .all()

        for student in results:
            print(f"  {student.full_name:20} {student.class_year.class_name:10} {student.house.house_name}")

    print("\n" + "="*70)
    print("✅ Demo Complete!")
    print("="*70)
    print("\nKey Differences from Raw SQLAlchemy:")
    print("  1. Use Model.query instead of session.query(Model)")
    print("  2. No session management - db.session is automatic!")
    print("  3. All inside app.app_context() (Flask handles this in routes)")
    print("  4. Simple: db.session.add(), db.session.commit()")
    print("  5. Models inherit from db.Model, not Base")
    print("\nKey Takeaways:")
    print("  • No manual SQL strings needed")
    print("  • Results are Python objects, not tuples")
    print("  • Relationships work automatically (student.house.house_name)")
    print("  • IDE autocomplete works!")
    print("  • Much easier than raw sqlite3")
    print("\nNext Steps:")
    print("  → Read FLASK_SQLALCHEMY_GUIDE.md")
    print("  → Start migrating one route at a time")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have Flask-SQLAlchemy installed:")
        print("  pip install Flask-SQLAlchemy")
