from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    equipment = db.relationship('Equipment', backref='category', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Equipment(db.Model):
    __tablename__ = 'equipment'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    description = db.Column(db.Text)
    purchase_date = db.Column(db.Date)
    value = db.Column(db.Float)
    status = db.Column(db.String(20), default='available')  # available, borrowed, maintenance, retired
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    borrowing_records = db.relationship('BorrowingRecord', backref='equipment', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Equipment {self.name}>'

class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    head = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    borrowing_records = db.relationship('BorrowingRecord', backref='department', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Department {self.name}>'

class BorrowingRecord(db.Model):
    __tablename__ = 'borrowing_records'
    
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    borrowed_by = db.Column(db.String(100), nullable=False)
    borrowed_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime)
    expected_return = db.Column(db.DateTime)
    purpose = db.Column(db.Text)
    status = db.Column(db.String(20), default='borrowed')  # borrowed, returned, overdue
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_overdue(self):
        if self.expected_return and not self.return_date:
            return datetime.utcnow() > self.expected_return
        return False
    
    def __repr__(self):
        return f'<BorrowingRecord {self.equipment_id} by {self.borrowed_by}> '