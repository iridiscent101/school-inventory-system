from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from models import db, Category, Equipment, Department, BorrowingRecord

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school_inventory.db'
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# ==================== DASHBOARD ====================
@app.route('/')
def dashboard():
    total_equipment = Equipment.query.count()
    available = Equipment.query.filter_by(status='available').count()
    borrowed = Equipment.query.filter_by(status='borrowed').count()
    maintenance = Equipment.query.filter_by(status='maintenance').count()
    
    active_borrowings = BorrowingRecord.query.filter_by(status='borrowed').count()
    overdue = BorrowingRecord.query.filter(
        BorrowingRecord.expected_return < datetime.utcnow(),
        BorrowingRecord.return_date == None
    ).count()
    
    recent_records = BorrowingRecord.query.order_by(BorrowingRecord.borrowed_date.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         total_equipment=total_equipment,
                         available=available,
                         borrowed=borrowed,
                         maintenance=maintenance,
                         active_borrowings=active_borrowings,
                         overdue=overdue,
                         recent_records=recent_records)

# ==================== EQUIPMENT ====================
@app.route('/equipment')
def equipment_list():
    category = request.args.get('category')
    status = request.args.get('status')
    search = request.args.get('search')
    
    query = Equipment.query
    
    if category:
        query = query.filter_by(category_id=category)
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(Equipment.name.ilike(f'%{search}%') | Equipment.code.ilike(f'%{search}%'))
    
    equipment = query.order_by(Equipment.created_at.desc()).all()
    categories = Category.query.all()
    
    return render_template('equipment/list.html', equipment=equipment, categories=categories)

@app.route('/equipment/new', methods=['GET', 'POST'])
def add_equipment():
    if request.method == 'POST':
        try:
            new_equipment = Equipment(
                name=request.form['name'],
                code=request.form['code'],
                category_id=request.form['category_id'],
                description=request.form.get('description'),
                purchase_date=datetime.strptime(request.form.get('purchase_date', ''), '%Y-%m-%d').date() if request.form.get('purchase_date') else None,
                value=float(request.form.get('value', 0)) if request.form.get('value') else None,
                location=request.form.get('location'),
                status='available'
            )
            db.session.add(new_equipment)
            db.session.commit()
            flash('Equipment added successfully!', 'success')
            return redirect(url_for('equipment_list'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    categories = Category.query.all()
    return render_template('equipment/add.html', categories=categories)

@app.route('/equipment/<int:id>/edit', methods=['GET', 'POST'])
def edit_equipment(id):
    equipment = Equipment.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            equipment.name = request.form['name']
            equipment.code = request.form['code']
            equipment.category_id = request.form['category_id']
            equipment.description = request.form.get('description')
            equipment.location = request.form.get('location')
            equipment.status = request.form['status']
            
            if request.form.get('purchase_date'):
                equipment.purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date()
            if request.form.get('value'):
                equipment.value = float(request.form['value'])
            
            db.session.commit()
            flash('Equipment updated successfully!', 'success')
            return redirect(url_for('equipment_list'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    categories = Category.query.all()
    return render_template('equipment/edit.html', equipment=equipment, categories=categories)

@app.route('/equipment/<int:id>')
def view_equipment(id):
    equipment = Equipment.query.get_or_404(id)
    borrowing_history = BorrowingRecord.query.filter_by(equipment_id=id).order_by(BorrowingRecord.borrowed_date.desc()).all()
    return render_template('equipment/view.html', equipment=equipment, borrowing_history=borrowing_history)

# ==================== BORROWING ====================
@app.route('/borrowing')
def borrowing_list():
    status = request.args.get('status')
    department = request.args.get('department')
    
    query = BorrowingRecord.query
    
    if status:
        query = query.filter_by(status=status)
    if department:
        query = query.filter_by(department_id=department)
    
    borrowing_records = query.order_by(BorrowingRecord.borrowed_date.desc()).all()
    departments = Department.query.all()
    
    return render_template('borrowing/list.html', borrowing_records=borrowing_records, departments=departments)

@app.route('/borrowing/new', methods=['GET', 'POST'])
def new_borrowing():
    if request.method == 'POST':
        try:
            equipment_id = request.form['equipment_id']
            equipment = Equipment.query.get_or_404(equipment_id)
            
            if equipment.status != 'available':
                flash(f'Equipment is not available (Status: {equipment.status})', 'warning')
                return redirect(url_for('new_borrowing'))
            
            borrowed_date = datetime.now()
            expected_return = borrowed_date + timedelta(days=int(request.form.get('duration', 7)))
            
            borrowing_record = BorrowingRecord(
                equipment_id=equipment_id,
                department_id=request.form['department_id'],
                borrowed_by=request.form['borrowed_by'],
                borrowed_date=borrowed_date,
                expected_return=expected_return,
                purpose=request.form.get('purpose'),
                status='borrowed'
            )
            
            equipment.status = 'borrowed'
            db.session.add(borrowing_record)
            db.session.commit()
            flash('Equipment borrowed successfully!', 'success')
            return redirect(url_for('borrowing_list'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    equipment = Equipment.query.filter_by(status='available').all()
    departments = Department.query.all()
    return render_template('borrowing/new.html', equipment=equipment, departments=departments)

@app.route('/borrowing/<int:id>/return', methods=['GET', 'POST'])
def return_equipment(id):
    borrowing_record = BorrowingRecord.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            borrowing_record.return_date = datetime.now()
            borrowing_record.status = 'returned'
            borrowing_record.notes = request.form.get('notes')
            
            borrowing_record.equipment.status = 'available'
            
            db.session.commit()
            flash('Equipment returned successfully!', 'success')
            return redirect(url_for('borrowing_list'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('borrowing/return.html', borrowing_record=borrowing_record)

# ==================== CATEGORIES ====================
@app.route('/categories')
def categories():
    categories = Category.query.all()
    return render_template('categories/list.html', categories=categories)

@app.route('/category/new', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        try:
            new_category = Category(
                name=request.form['name'],
                description=request.form.get('description')
            )
            db.session.add(new_category)
            db.session.commit()
            flash('Category added successfully!', 'success')
            return redirect(url_for('categories'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('categories/add.html')

# ==================== DEPARTMENTS ====================
@app.route('/departments')
def departments():
    departments = Department.query.all()
    return render_template('departments/list.html', departments=departments)

@app.route('/department/new', methods=['GET', 'POST'])
def add_department():
    if request.method == 'POST':
        try:
            new_dept = Department(
                name=request.form['name'],
                head=request.form.get('head'),
                phone=request.form.get('phone'),
                email=request.form.get('email')
            )
            db.session.add(new_dept)
            db.session.commit()
            flash('Department added successfully!', 'success')
            return redirect(url_for('departments'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('departments/add.html')

# ==================== REPORTS ====================
@app.route('/reports')
def reports():
    category_stats = db.session.query(
        Category.name,
        db.func.count(Equipment.id).label('total'),
        db.func.sum(db.case((Equipment.status == 'available', 1), else_=0)).label('available'),
        db.func.sum(db.case((Equipment.status == 'borrowed', 1), else_=0)).label('borrowed')
    ).outerjoin(Equipment).group_by(Category.id, Category.name).all()
    
    dept_borrowing = db.session.query(
        Department.name,
        db.func.count(BorrowingRecord.id).label('total_borrows'),
        db.func.sum(db.case((BorrowingRecord.status == 'borrowed', 1), else_=0)).label('active')
    ).outerjoin(BorrowingRecord).group_by(Department.id, Department.name).all()
    
    return render_template('reports.html', category_stats=category_stats, dept_borrowing=dept_borrowing)

if __name__ == '__main__':
    app.run(debug=True)