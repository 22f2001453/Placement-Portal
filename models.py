from flask_login import UserMixin
from database import db
from datetime import datetime

class Admin(UserMixin, db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def get_id(self):
        return f"admin_{self.id}"

class Student(UserMixin, db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    resume = db.Column(db.String(255), nullable=True) # path to resume
    password = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='active') # active/blacklisted
    
    applications = db.relationship('Application', backref='student', lazy=True)

    def get_id(self):
        return f"student_{self.id}"

class Company(UserMixin, db.Model):
    __tablename__ = 'company'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), unique=True, nullable=False)
    hr_contact = db.Column(db.String(150), nullable=False)
    website = db.Column(db.String(255), nullable=True)
    password = db.Column(db.String(255), nullable=False)
    approval_status = db.Column(db.String(20), default='pending') # pending/approved/rejected
    
    drives = db.relationship('PlacementDrive', backref='company', lazy=True)

    def get_id(self):
        return f"company_{self.id}"

class PlacementDrive(db.Model):
    __tablename__ = 'placement_drive'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    eligibility = db.Column(db.String(255), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending') # pending/approved/closed
    
    applications = db.relationship('Application', backref='drive', lazy=True)

class Application(db.Model):
    __tablename__ = 'application'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Applied') # Applied / Shortlisted / Selected / Rejected
    
    __table_args__ = (db.UniqueConstraint('student_id', 'drive_id', name='_student_drive_uc'),)
