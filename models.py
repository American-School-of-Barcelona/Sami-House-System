"""
SQLAlchemy Models for House Points System
Converts raw SQL to Python ORM
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class House(db.Model):
    """House model - represents the 4 houses (Athena, Poseidon, Artemis, Apollo)"""
    __tablename__ = 'HOUSES'

    house_id = db.Column(db.Integer, primary_key=True)
    house_name = db.Column(db.Text, nullable=False)
    logo_sq = db.Column(db.Text)
    logo_large = db.Column(db.Text)
    color = db.Column(db.Text)

    # Relationships
    students = db.relationship('Student', backref='house', lazy=True)
    event_results = db.relationship('EventResult', backref='house', lazy=True)

    def __repr__(self):
        return f'<House {self.house_name}>'

    @classmethod
    def get_all(cls):
        """Get all houses ordered by house_id"""
        return cls.query.order_by(cls.house_id).all()

    @classmethod
    def get_by_name(cls, name):
        """Get house by name"""
        return cls.query.filter_by(house_name=name).first()


class ClassYear(db.Model):
    """Class Year model - represents grade levels (Freshman, Sophomore, Junior, Senior)"""
    __tablename__ = 'CLASS_YEARS'

    class_year_id = db.Column(db.Integer, primary_key=True)
    grad_year = db.Column(db.Integer, nullable=False)
    class_name = db.Column(db.Text, nullable=False)
    display_order = db.Column(db.Integer, nullable=False)

    # Relationships
    students = db.relationship('Student', backref='class_year', lazy=True)

    def __repr__(self):
        return f'<ClassYear {self.class_name}>'

    @classmethod
    def get_all(cls):
        """Get all class years ordered by display_order"""
        return cls.query.order_by(cls.display_order).all()

    @classmethod
    def get_by_name(cls, name):
        """Get class year by name"""
        return cls.query.filter_by(class_name=name).first()


class Student(db.Model):
    """Student model - represents students in the house system"""
    __tablename__ = 'STUDENTS'

    student_id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.Text, nullable=False)
    lname = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text)
    house_id = db.Column(db.Integer, db.ForeignKey('HOUSES.house_id'), nullable=False)
    class_year_id = db.Column(db.Integer, db.ForeignKey('CLASS_YEARS.class_year_id'), nullable=False)

    def __repr__(self):
        return f'<Student {self.fname} {self.lname}>'

    @property
    def full_name(self):
        return f'{self.fname} {self.lname}'

    @classmethod
    def get_all(cls):
        """Get all students"""
        return cls.query.all()

    @classmethod
    def get_by_house(cls, house_id):
        """Get all students in a specific house"""
        return cls.query.filter_by(house_id=house_id).all()

    @classmethod
    def search(cls, query):
        """Search students by name or email"""
        search_term = f'%{query}%'
        return cls.query.filter(
            db.or_(
                cls.fname.ilike(search_term),
                cls.lname.ilike(search_term),
                cls.email.ilike(search_term)
            )
        ).all()

    @classmethod
    def count_by_house(cls, house_id):
        """Count students in a house"""
        return cls.query.filter_by(house_id=house_id).count()

    @classmethod
    def get_siblings_by_last_name(cls, last_name):
        """Get all students with a specific last name"""
        return cls.query.filter(
            db.func.lower(cls.lname) == last_name.lower()
        ).all()


class Event(db.Model):
    """Event model - represents house competition events"""
    __tablename__ = 'EVENTS'

    event_id = db.Column(db.Integer, primary_key=True)
    event_date = db.Column(db.Text, nullable=False)
    event_desc = db.Column(db.Text, nullable=False)
    event_type = db.Column(db.Text)
    created_at = db.Column(db.Text, default=lambda: datetime.now().isoformat())

    # Relationships
    results = db.relationship('EventResult', backref='event', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Event {self.event_desc}>'

    @classmethod
    def get_all(cls):
        """Get all events ordered by date descending"""
        return cls.query.order_by(cls.event_date.desc()).all()

    @classmethod
    def get_recent(cls, limit=10):
        """Get most recent events"""
        return cls.query.order_by(cls.event_date.desc()).limit(limit).all()


class EventResult(db.Model):
    """Event Result model - represents house results for each event"""
    __tablename__ = 'EVENT_RESULTS'

    event_id = db.Column(db.Integer, db.ForeignKey('EVENTS.event_id'), primary_key=True, nullable=False)
    house_id = db.Column(db.Integer, db.ForeignKey('HOUSES.house_id'), primary_key=True, nullable=False)
    points_earned = db.Column(db.Integer, nullable=False)
    rank = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<EventResult Event:{self.event_id} House:{self.house_id} Points:{self.points_earned}>'

    @classmethod
    def get_total_points_by_house(cls, house_id):
        """Get total points for a house"""
        result = db.session.query(db.func.sum(cls.points_earned)).filter_by(house_id=house_id).scalar()
        return result or 0

    @classmethod
    def get_all_house_totals(cls):
        """Get total points for all houses"""
        return db.session.query(
            cls.house_id,
            db.func.sum(cls.points_earned).label('total_points')
        ).group_by(cls.house_id).all()


class User(db.Model, UserMixin):
    """User model - represents authenticated users (admins, reps)"""
    __tablename__ = 'USERS'

    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False, default='guest')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return str(self.user_id)

    def __repr__(self):
        return f'<User {self.email}>'

    @classmethod
    def get_by_email(cls, email):
        """Get user by email (case-insensitive)"""
        return cls.query.filter(db.func.lower(cls.email) == email.lower()).first()

    @classmethod
    def get_by_id(cls, user_id):
        """Get user by ID"""
        return cls.query.get(int(user_id))


class AuthorizedExecutive(db.Model):
    """Authorized Executive model - represents authorized admin/rep emails"""
    __tablename__ = 'AUTHORIZED_EXECUTIVES'

    email = db.Column(db.Text, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.Text, default='admin')
    grade_level = db.Column(db.Text)

    def __repr__(self):
        return f'<AuthorizedExecutive {self.email}>'

    @classmethod
    def get_by_email(cls, email):
        """Get authorized executive by email (case-insensitive)"""
        return cls.query.filter(db.func.lower(cls.email) == email.lower()).first()

    @classmethod
    def is_authorized(cls, email):
        """Check if email is authorized"""
        return cls.get_by_email(email) is not None

    @classmethod
    def get_all_emails(cls):
        """Get list of all authorized emails"""
        return [e.email for e in cls.query.all()]

    @classmethod
    def get_executives(cls):
        """Get all executives (admin role)"""
        return cls.query.filter_by(role='admin').all()

    @classmethod
    def get_representatives(cls):
        """Get all representatives (rep role)"""
        return cls.query.filter_by(role='rep').order_by(cls.grade_level).all()
