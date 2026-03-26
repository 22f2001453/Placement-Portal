from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
from datetime import datetime

from config import Config
from database import db
from models import Admin, Student, Company, PlacementDrive, Application

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    try:
        user_type, uid = user_id.split('_')
        uid = int(uid)
        if user_type == 'admin':
            return Admin.query.get(uid)
        elif user_type == 'student':
            return Student.query.get(uid)
        elif user_type == 'company':
            return Company.query.get(uid)
    except:
        return None
    return None

def init_db():
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        if not Admin.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('admin123')
            admin = Admin(username='admin', password=hashed_pw)
            db.session.add(admin)
            db.session.commit()

# --- AUTH ROUTES ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        if isinstance(current_user, Admin):
            return redirect(url_for('admin_dashboard'))
        elif isinstance(current_user, Company):
            return redirect(url_for('company_dashboard'))
        elif isinstance(current_user, Student):
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        identifier = request.form.get('identifier') # username, email, or company name
        password = request.form.get('password')

        user = None
        if role == 'admin':
            user = Admin.query.filter_by(username=identifier).first()
        elif role == 'student':
            user = Student.query.filter_by(email=identifier).first()
        elif role == 'company':
            user = Company.query.filter_by(company_name=identifier).first()

        if user and check_password_hash(user.password, password):
            if role == 'student' and user.status == 'blacklisted':
                flash('Your account is blacklisted. Contact admin.', 'danger')
                return redirect(url_for('login'))
            if role == 'company':
                if user.approval_status == 'pending':
                    flash('Your account is pending admin approval.', 'warning')
                    return redirect(url_for('login'))
                if user.approval_status == 'rejected':
                    flash('Your account was rejected by admin.', 'danger')
                    return redirect(url_for('login'))
                if user.approval_status == 'blacklisted':
                    flash('Your account is blacklisted. Contact admin.', 'danger')
                    return redirect(url_for('login'))

            login_user(user)
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'company':
                return redirect(url_for('company_dashboard'))
            elif role == 'student':
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid credentials or role mismatch', 'danger')

    return render_template('login.html')

@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')

        if Student.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register_student'))

        hashed_pw = generate_password_hash(password)
        new_student = Student(name=name, email=email, phone=phone, password=hashed_pw)
        db.session.add(new_student)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register_student.html')

@app.route('/register_company', methods=['GET', 'POST'])
def register_company():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        hr_contact = request.form.get('hr_contact')
        website = request.form.get('website')
        password = request.form.get('password')

        if Company.query.filter_by(company_name=company_name).first():
            flash('Company name already registered', 'danger')
            return redirect(url_for('register_company'))

        hashed_pw = generate_password_hash(password)
        new_company = Company(company_name=company_name, hr_contact=hr_contact, website=website, password=hashed_pw)
        db.session.add(new_company)
        db.session.commit()
        flash('Registration successful! Please wait for admin approval.', 'success')
        return redirect(url_for('login'))

    return render_template('register_company.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# --- ADMIN ROUTES ---
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not isinstance(current_user, Admin):
        return "Unauthorized", 403
    
    total_students = Student.query.count()
    total_companies = Company.query.count()
    total_drives = PlacementDrive.query.count()
    total_applications = Application.query.count()

    pending_companies = Company.query.filter_by(approval_status='pending').all()
    pending_drives = PlacementDrive.query.filter_by(status='pending').all()

    return render_template('admin_dashboard.html', 
                            s_count=total_students, c_count=total_companies,
                            d_count=total_drives, a_count=total_applications,
                            pending_companies=pending_companies,
                            pending_drives=pending_drives)

@app.route('/admin/approve_company/<int:id>/<action>')
@login_required
def approve_company(id, action):
    if not isinstance(current_user, Admin):
        return "Unauthorized", 403
    company = Company.query.get_or_404(id)
    if action == 'approve':
        company.approval_status = 'approved'
        flash(f'Company {company.company_name} approved', 'success')
    elif action == 'reject':
        company.approval_status = 'rejected'
        flash(f'Company {company.company_name} rejected', 'warning')
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve_drive/<int:id>/<action>')
@login_required
def approve_drive(id, action):
    if not isinstance(current_user, Admin):
        return "Unauthorized", 403
    drive = PlacementDrive.query.get_or_404(id)
    if action == 'approve':
        drive.status = 'approved'
        flash(f'Drive {drive.job_title} approved', 'success')
    elif action == 'reject':
        drive.status = 'rejected' # we'll treat rejected as closed or delete it
        flash(f'Drive {drive.job_title} rejected', 'warning')
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/students', methods=['GET', 'POST'])
@login_required
def admin_students():
    if not isinstance(current_user, Admin):
        return "Unauthorized", 403
    query = request.form.get('q', '')
    if query:
        students = Student.query.filter(Student.name.ilike(f'%{query}%') | Student.id.ilike(f'%{query}%')).all()
    else:
        students = Student.query.all()
    return render_template('admin_students.html', students=students, q=query)

@app.route('/admin/companies', methods=['GET', 'POST'])
@login_required
def admin_companies():
    if not isinstance(current_user, Admin):
        return "Unauthorized", 403
    query = request.form.get('q', '')
    if query:
        companies = Company.query.filter(Company.company_name.ilike(f'%{query}%')).all()
    else:
        companies = Company.query.all()
    return render_template('admin_companies.html', companies=companies, q=query)


@app.route('/admin/blacklist_student/<int:id>')
@login_required
def blacklist_student(id):
    if not isinstance(current_user, Admin):
        return "Unauthorized", 403
    student = Student.query.get_or_404(id)
    student.status = 'blacklisted' if student.status == 'active' else 'active'
    db.session.commit()
    flash(f"Student status changed to {student.status}", 'info')
    return redirect(url_for('admin_students'))

@app.route('/admin/blacklist_company/<int:id>')
@login_required
def blacklist_company(id):
    if not isinstance(current_user, Admin):
        return "Unauthorized", 403
    company = Company.query.get_or_404(id)
    company.approval_status = 'blacklisted' if company.approval_status != 'blacklisted' else 'approved'
    db.session.commit()
    flash(f"Company status changed to {company.approval_status}", 'info')
    return redirect(url_for('admin_companies'))

@app.route('/admin/applications')
@login_required
def admin_applications():
    if not isinstance(current_user, Admin):
        return "Unauthorized", 403
    applications = Application.query.all()
    return render_template('admin_applications.html', applications=applications)

# --- COMPANY ROUTES ---
@app.route('/company/dashboard')
@login_required
def company_dashboard():
    if not isinstance(current_user, Company):
        return "Unauthorized", 403
    
    drives_count = PlacementDrive.query.filter_by(company_id=current_user.id).count()
    return render_template('company_dashboard.html', company=current_user, drives_count=drives_count)

@app.route('/company/drives')
@login_required
def company_drives():
    if not isinstance(current_user, Company):
        return "Unauthorized", 403
    drives = PlacementDrive.query.filter_by(company_id=current_user.id).all()
    return render_template('drives.html', drives=drives, role='company')

@app.route('/company/create_drive', methods=['GET', 'POST'])
@login_required
def create_drive():
    if not isinstance(current_user, Company):
        return "Unauthorized", 403
    if request.method == 'POST':
        job_title = request.form.get('job_title')
        job_description = request.form.get('job_description')
        eligibility = request.form.get('eligibility')
        deadline_str = request.form.get('deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()

        new_drive = PlacementDrive(company_id=current_user.id, job_title=job_title, 
                                   job_description=job_description, eligibility=eligibility, 
                                   deadline=deadline)
        db.session.add(new_drive)
        db.session.commit()
        flash('Drive created and pending admin approval', 'success')
        return redirect(url_for('company_drives'))

    return render_template('create_drive.html')

@app.route('/company/edit_drive/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_drive(id):
    if not isinstance(current_user, Company):
        return "Unauthorized", 403
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.id:
        return "Unauthorized", 403

    if request.method == 'POST':
        drive.job_title = request.form.get('job_title')
        drive.job_description = request.form.get('job_description')
        drive.eligibility = request.form.get('eligibility')
        deadline_str = request.form.get('deadline')
        if deadline_str:
            drive.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        db.session.commit()
        flash('Drive updated', 'success')
        return redirect(url_for('company_drives'))
    return render_template('create_drive.html', drive=drive)

@app.route('/company/close_drive/<int:id>')
@login_required
def close_drive(id):
    if not isinstance(current_user, Company):
        return "Unauthorized", 403
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id == current_user.id:
        drive.status = 'closed'
        db.session.commit()
        flash('Drive closed', 'info')
    return redirect(url_for('company_drives'))

@app.route('/company/applications/<int:drive_id>')
@login_required
def company_applications(drive_id):
    if not isinstance(current_user, Company):
        return "Unauthorized", 403
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.id:
        return "Unauthorized", 403
    apps = Application.query.filter_by(drive_id=drive_id).all()
    return render_template('applications.html', applications=apps, drive=drive, role='company')

@app.route('/company/update_application/<int:app_id>', methods=['POST'])
@login_required
def update_application(app_id):
    if not isinstance(current_user, Company):
        return "Unauthorized", 403
    application = Application.query.get_or_404(app_id)
    if application.drive.company_id != current_user.id:
        return "Unauthorized", 403
    
    new_status = request.form.get('status')
    application.status = new_status
    db.session.commit()
    flash('Application status updated', 'success')
    return redirect(url_for('company_applications', drive_id=application.drive_id))


# --- STUDENT ROUTES ---
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if not isinstance(current_user, Student):
        return "Unauthorized", 403
    return render_template('student_dashboard.html')

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if not isinstance(current_user, Student):
        return "Unauthorized", 403
    student = Student.query.get(current_user.id)
    
    if request.method == 'POST':
        student.name = request.form.get('name')
        student.phone = request.form.get('phone')
        
        resume_file = request.files.get('resume')
        if resume_file and resume_file.filename != '':
            filename = f"student_{student.id}_{resume_file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume_file.save(filepath)
            student.resume = filename

        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('student_profile'))
        
    return render_template('profile.html', student=student)

@app.route('/student/drives')
@login_required
def student_drives():
    if not isinstance(current_user, Student):
        return "Unauthorized", 403
    # Show active and approved drives
    today = datetime.utcnow().date()
    drives = PlacementDrive.query.filter(PlacementDrive.status == 'approved', PlacementDrive.deadline >= today).all()
    
    # Get IDs of drives already applied to
    applied_ids = [app.drive_id for app in current_user.applications]
    
    return render_template('drives.html', drives=drives, role='student', applied_ids=applied_ids)

@app.route('/student/apply/<int:drive_id>')
@login_required
def apply_drive(drive_id):
    if not isinstance(current_user, Student):
        return "Unauthorized", 403
        
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    if drive.status != 'approved' or drive.deadline < datetime.utcnow().date():
        flash('This drive is not open for applications', 'danger')
        return redirect(url_for('student_drives'))

    existing_app = Application.query.filter_by(student_id=current_user.id, drive_id=drive_id).first()
    if existing_app:
        flash('You have already applied to this drive', 'warning')
        return redirect(url_for('student_drives'))

    new_app = Application(student_id=current_user.id, drive_id=drive_id)
    db.session.add(new_app)
    db.session.commit()
    flash(f'Successfully applied to {drive.job_title} at {drive.company.company_name}', 'success')
    return redirect(url_for('student_applications'))

@app.route('/student/applications')
@login_required
def student_applications():
    if not isinstance(current_user, Student):
        return "Unauthorized", 403
    apps = Application.query.filter_by(student_id=current_user.id).all()
    return render_template('applications.html', applications=apps, role='student')


if __name__ == '__main__':
    if not os.path.exists('instance'):
        os.makedirs('instance')
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    
    init_db()
    app.run(debug=True)
