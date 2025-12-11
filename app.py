"""
GTMS Admin Panel - Complete User & License Management
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import hashlib
import os
from pathlib import Path
from utils.invoice_generator import InvoiceGenerator

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
print("USING DATABASE:", app.config['SQLALCHEMY_DATABASE_URI'])


db = SQLAlchemy(app)   # <-- ONLY ONE TIME IN THE WHOLE PROJECT

from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    """Decorator for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def permission_required(flag_name):
    """Require a specific permission on AdminUser."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'admin_id' not in session:
                return redirect(url_for('admin_login'))

            admin = AdminUser.query.get(session['admin_id'])
            if not admin or not getattr(admin, flag_name, False):
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return decorated
    return decorator







# ==================
# DATABASE MODELS
# ==================

class AdminUser(db.Model):
    """Admin / Employee accounts for the license server"""
    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(20), unique=True, nullable=True)  # e.g. EMP001
    full_name = db.Column(db.String(100), nullable=True)

    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))

    role = db.Column(db.String(20), default='Staff', nullable=False)  # SuperAdmin / Staff

    # Employee lifecycle
    join_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    leave_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # working or left company

    # Permissions
    can_manage_clients = db.Column(db.Boolean, default=False, nullable=False)
    can_manage_licenses = db.Column(db.Boolean, default=False, nullable=False)
    can_manage_payments = db.Column(db.Boolean, default=False, nullable=False)
    can_manage_users = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)



class GTMSUser(db.Model):
    """GTMS Application Users"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='User')  # Admin, Manager, User
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    company_name = db.Column(db.String(200))
    
    # License info
    license_id = db.Column(db.Integer, db.ForeignKey('license.id'))
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationship
    devices = db.relationship('DeviceAccess', backref='user', lazy=True)
    
    def set_password(self, password):
        """Set hashed password (SHA-256 for GTMS compatibility)"""
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

class Client(db.Model):
    """Customer / company using your software"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    gst_number = db.Column(db.String(30))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    licenses = db.relationship('License', backref='client', lazy=True)
    subscriptions = db.relationship('Subscription', backref='client', lazy=True)
    payments = db.relationship('Payment', backref='client', lazy=True)
    invoices = db.relationship('Invoice', backref='client', lazy=True)


class Subscription(db.Model):
    """Subscription management for clients"""
    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    license_id = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=True)

    plan_name = db.Column(db.String(100), nullable=False)
    plan_type = db.Column(db.String(50), default='yearly')  # monthly, quarterly, yearly, lifetime

    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')

    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    next_billing_date = db.Column(db.DateTime)

    status = db.Column(db.String(30), default='active')  # active, expired, cancelled, suspended
    auto_renew = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)

    payments = db.relationship('Payment', backref='subscription', lazy=True)


class Payment(db.Model):
    """Payment tracking"""
    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=True)
    license_id = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=True)

    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100))

    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_for = db.Column(db.String(100))

    invoice_number = db.Column(db.String(50), unique=True)
    invoice_generated = db.Column(db.Boolean, default=False)
    invoice_path = db.Column(db.String(255))

    status = db.Column(db.String(30), default='completed')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))
    notes = db.Column(db.Text)


class Invoice(db.Model):
    """Invoice generation and tracking"""
    id = db.Column(db.Integer, primary_key=True)

    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)

    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=True)

    subtotal = db.Column(db.Float, nullable=False)
    tax_rate = db.Column(db.Float, default=18.0)
    tax_amount = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)

    items = db.Column(db.Text)  # JSON string
    status = db.Column(db.String(30), default='unpaid')
    pdf_path = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)


class RenewalLog(db.Model):
    """Track all renewals and extensions"""
    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    license_id = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=True)

    old_expiry_date = db.Column(db.DateTime)
    new_expiry_date = db.Column(db.DateTime, nullable=False)

    renewal_type = db.Column(db.String(50), nullable=False)  # license_renewal, subscription_renewal, extension
    amount = db.Column(db.Float)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=True)

    renewed_by = db.Column(db.String(100))  # Admin username
    renewal_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    # Relationships
    client = db.relationship('Client', backref='renewals')






class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)
    license_key = db.Column(db.String(100), unique=True, nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    product_name = db.Column(db.String(100), default='GTMS', nullable=False)  # ✅



class DeviceAccess(db.Model):
    """Track device access"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('gtms_user.id'))
    license_id = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=False)
    
    # Device info
    hardware_id = db.Column(db.String(100), nullable=False)
    device_name = db.Column(db.String(100))
    os_info = db.Column(db.String(100))
    ip_address = db.Column(db.String(50))
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    first_access = db.Column(db.DateTime, default=datetime.utcnow)
    last_access = db.Column(db.DateTime, default=datetime.utcnow)
    access_count = db.Column(db.Integer, default=1)


class ActivityLog(db.Model):
    """Activity logging"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('gtms_user.id'))
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AdminActivityLog(db.Model):
    """Log actions performed by admin/employees"""
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    """Software products (GTMS, HT Management, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    default_max_users = db.Column(db.Integer, default=5)
    default_max_devices = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    licenses = db.relationship('License', backref='product', lazy=True)




    # ==================
# ROUTES - Employees Management (Admin users)
# ==================
@app.route('/admin/employees/<int:admin_id>')
@login_required
@permission_required('can_manage_users')
def employee_detail(admin_id):
    """View employee details and recent activity"""
    emp = AdminUser.query.get_or_404(admin_id)
    logs = AdminActivityLog.query.filter_by(admin_id=admin_id) \
                                 .order_by(AdminActivityLog.timestamp.desc()) \
                                 .limit(50).all()
    return render_template('employee_detail.html', emp=emp, logs=logs)




@app.route('/admin/employees')
@login_required
@permission_required('can_manage_users')  # or a new can_manage_employees flag
def employees_list():
    """List all admin/employees"""
    employees = AdminUser.query.order_by(AdminUser.created_at.desc()).all()
    return render_template('employees.html', employees=employees)


@app.route('/admin/employees/edit/<int:admin_id>', methods=['POST'])
@login_required
@permission_required('can_manage_users')
def edit_employee(admin_id):
    """Edit admin/employee info and permissions"""
    admin = AdminUser.query.get_or_404(admin_id)
    data = request.form

    admin.employee_code = data.get('employee_code') or admin.employee_code
    admin.full_name = data.get('full_name') or admin.full_name
    admin.email = data.get('email') or admin.email
    admin.phone = data.get('phone') or admin.phone
    admin.role = data.get('role') or admin.role

    # Status + dates
    status = data.get('status', 'active')
    admin.is_active = (status == 'active')
    if status == 'left':
        leave_date_str = data.get('leave_date')
        if leave_date_str:
            admin.leave_date = datetime.fromisoformat(leave_date_str)
        else:
            admin.leave_date = datetime.utcnow()
    else:
        admin.leave_date = None

    # Permissions (checkboxes)
    admin.can_manage_clients = bool(data.get('can_manage_clients'))
    admin.can_manage_licenses = bool(data.get('can_manage_licenses'))
    admin.can_manage_payments = bool(data.get('can_manage_payments'))
    admin.can_manage_users = bool(data.get('can_manage_users'))

    # New password (optional)
    new_password = data.get('new_password', '').strip()
    if new_password:
        admin.set_password(new_password)

    db.session.commit()
    flash(f'Employee "{admin.username}" updated successfully!', 'success')
    return redirect(url_for('employees_list'))

@app.route('/admin/employees/add', methods=['GET', 'POST'])
@login_required
@permission_required('can_manage_users')
def add_employee():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form.get('phone')
        role = request.form.get('role', 'Staff')
        status = request.form.get('status', 'active')
        join_date = request.form.get('join_date')  # parse if you store dates
        password = request.form['password']

        emp = AdminUser(
            username=username,
            email=email,
            phone=phone,
            role=role,
            is_active=(status == 'active'),
            can_manage_clients=bool(request.form.get('can_manage_clients')),
            can_manage_licenses=bool(request.form.get('can_manage_licenses')),
            can_manage_payments=bool(request.form.get('can_manage_payments')),
            can_manage_users=bool(request.form.get('can_manage_users')),
        )

        if join_date:
            emp.join_date = datetime.fromisoformat(join_date)

        emp.set_password(password)
        db.session.add(emp)
        db.session.commit()
        flash('Employee created successfully', 'success')
        return redirect(url_for('employees_list'))

    return render_template('employee_add.html')




# ==================
# ROUTES - Authentication
# ==================


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = AdminUser.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            session['admin_role'] = admin.role  # role field on AdminUser
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'error')

    return render_template('login.html')


@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('admin_login'))


# Decorators defined above; do not redefine them here.


# ==================
# ROUTES - Dashboard
# ==================


@app.route('/')
@app.route('/admin/dashboard')
@login_required
def dashboard():
    """Enhanced dashboard with expiry warnings and revenue"""

    # === LICENSE STATS ===
    total_licenses = License.query.count()
    active_licenses = License.query.filter_by(is_active=True).count()

    # Expiring in 7 days
    expiring_soon = License.query.filter(
        License.expiry_date <= datetime.utcnow() + timedelta(days=7),
        License.expiry_date >= datetime.utcnow(),
        License.is_active == True
    ).all()

    # Already expired
    expired_licenses = License.query.filter(
        License.expiry_date < datetime.utcnow(),
        License.is_active == True
    ).count()

    # === USER STATS ===
    total_users = GTMSUser.query.count()
    active_users = GTMSUser.query.filter_by(is_active=True).count()

    # === DEVICE STATS ===
    total_devices = DeviceAccess.query.count()
    active_devices = DeviceAccess.query.filter_by(is_active=True).count()

    # === CLIENT STATS ===
    total_clients = Client.query.count()
    active_clients = Client.query.filter_by(status='active').count()

    # === SUBSCRIPTION STATS ===
    total_subscriptions = Subscription.query.count()
    active_subscriptions = Subscription.query.filter_by(status='active').count()

    # Expiring subscriptions (30 days)
    expiring_subscriptions = Subscription.query.filter(
        Subscription.end_date <= datetime.utcnow() + timedelta(days=30),
        Subscription.end_date >= datetime.utcnow(),
        Subscription.status == 'active'
    ).all()

    # === PAYMENT & REVENUE STATS ===
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='completed').scalar() or 0

    # This month revenue
    first_day = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == 'completed',
        Payment.payment_date >= first_day
    ).scalar() or 0

    # Outstanding payments (pending/unpaid)
    outstanding_payments = db.session.query(db.func.sum(Payment.amount)).filter_by(status='pending').scalar() or 0
    outstanding_count = Payment.query.filter_by(status='pending').count()

    # === RECENT ACTIVITY ===
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    recent_payments = Payment.query.order_by(Payment.payment_date.desc()).limit(5).all()
    recent_renewals = RenewalLog.query.order_by(RenewalLog.renewal_date.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        total_licenses=total_licenses,
        active_licenses=active_licenses,
        expired_licenses=expired_licenses,
        expiring_soon=expiring_soon,
        expiring_soon_count=len(expiring_soon),

        total_users=total_users,
        active_users=active_users,

        total_devices=total_devices,
        active_devices=active_devices,

        total_clients=total_clients,
        active_clients=active_clients,

        total_subscriptions=total_subscriptions,
        active_subscriptions=active_subscriptions,
        expiring_subscriptions=expiring_subscriptions,
        expiring_subs_count=len(expiring_subscriptions),

        total_revenue=total_revenue,
        month_revenue=month_revenue,
        outstanding_payments=outstanding_payments,
        outstanding_count=outstanding_count,

        recent_logs=recent_logs,
        recent_payments=recent_payments,
        recent_renewals=recent_renewals
    )


@app.route('/admin/payments/outstanding')
@login_required
@permission_required('can_manage_payments')
def outstanding_payments():
    """Show outstanding/pending payments"""
    payments = Payment.query.filter_by(status='pending').order_by(Payment.payment_date.asc()).all()

    total_outstanding = db.session.query(db.func.sum(Payment.amount)).filter_by(status='pending').scalar() or 0
    pending_count = len(payments)

    # Overdue: pending for more than 30 days
    overdue_count = sum(1 for p in payments if (datetime.utcnow() - p.payment_date).days > 30)

    return render_template(
        'outstanding_payments.html',
        payments=payments,
        total_outstanding=total_outstanding,
        pending_count=pending_count,
        overdue_count=overdue_count,
        now=datetime.utcnow()
    )


@app.route('/admin/payments/mark-paid/<int:payment_id>', methods=['POST'])
@login_required
@permission_required('can_manage_payments')
def mark_payment_paid(payment_id):
    """Mark a payment as completed"""
    try:
        payment = Payment.query.get_or_404(payment_id)
        payment.status = 'completed'
        db.session.commit()

        return jsonify({'success': True, 'message': 'Payment marked as completed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500




# ==================
# ROUTES - User Management
# ==================


@app.route('/admin/users')
@login_required
@permission_required('can_manage_users')
def users_list():
    """List all GTMS users"""
    users = GTMSUser.query.order_by(GTMSUser.created_at.desc()).all()
    licenses = License.query.filter_by(is_active=True).all()
    return render_template('users.html', users=users, licenses=licenses)


@app.route('/admin/users/add', methods=['POST'])
@login_required
@permission_required('can_manage_users')
def add_user():
    """Add new GTMS user"""
    try:
        data = request.form

        if GTMSUser.query.filter_by(username=data['username']).first():
            flash('Username already exists!', 'error')
            return redirect(url_for('users_list'))

        # ✅ ENFORCE MAX USERS PER LICENSE
        license_id = data.get('license_id') or None
        if license_id:
            lic = License.query.get(int(license_id))
            if lic:
                current_users = GTMSUser.query.filter_by(license_id=lic.id).count()
                if current_users >= lic.max_users:
                    flash(f'User limit reached for this license (max {lic.max_users}).', 'error')
                    return redirect(url_for('users_list'))

        user = GTMSUser(
            username=data['username'],
            full_name=data['full_name'],
            role=data.get('role', 'User'),
            email=data.get('email'),
            phone=data.get('phone'),
            company_name=data.get('company_name'),
            license_id=license_id
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        flash(f'User {user.username} created successfully!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', 'error')

    return redirect(url_for('users_list'))


@app.route('/admin/users/edit/<int:user_id>', methods=['POST'])
@login_required
@permission_required('can_manage_users')
def edit_user(user_id):
    """Edit GTMS user"""
    try:
        user = GTMSUser.query.get_or_404(user_id)
        data = request.form

        # ✅ ENFORCE MAX USERS PER LICENSE WHEN CHANGING LICENSE
        new_license_id = data.get('license_id') or None
        if new_license_id:
            new_license_id_int = int(new_license_id)
            # Only check limit if license is changing
            if user.license_id != new_license_id_int:
                lic = License.query.get(new_license_id_int)
                if lic:
                    current_users = GTMSUser.query.filter_by(license_id=lic.id).count()
                    if current_users >= lic.max_users:
                        flash(f'User limit reached for this license (max {lic.max_users}).', 'error')
                        return redirect(url_for('users_list'))

        user.full_name = data.get('full_name', user.full_name)
        user.role = data.get('role', user.role)
        user.email = data.get('email', user.email)
        user.phone = data.get('phone', user.phone)
        user.company_name = data.get('company_name', user.company_name)
        user.license_id = new_license_id
        user.is_active = data.get('is_active') == 'true'

        if data.get('password'):
            user.set_password(data['password'])

        db.session.commit()

        flash(f'User {user.username} updated successfully!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'error')

    return redirect(url_for('users_list'))


@app.route('/admin/users/toggle-status/<int:user_id>/<int:is_active>', methods=['POST'])
@login_required
@permission_required('can_manage_users')
def toggle_user_status(user_id, is_active):
    """Toggle user active/inactive status"""
    try:
        user = GTMSUser.query.get_or_404(user_id)
        user.is_active = bool(is_active)
        db.session.commit()

        status = "activated" if is_active else "deactivated"
        flash(f'User {user.username} {status} successfully!', 'success')

        return jsonify({'success': True, 'message': f'User {status}'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@permission_required('can_manage_users')
def delete_user(user_id):
    """Delete GTMS user"""
    try:
        user = GTMSUser.query.get_or_404(user_id)
        username = user.username

        db.session.delete(user)
        db.session.commit()

        flash(f'User {username} deleted successfully!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')

    return redirect(url_for('users_list'))


# ==================
# ROUTES - Device Management
# ==================


@app.route('/admin/devices')
@login_required
def devices_list():
    """List all devices"""
    devices = DeviceAccess.query.order_by(DeviceAccess.last_access.desc()).all()
    return render_template('devices.html', devices=devices)


@app.route('/admin/devices/deactivate/<int:device_id>', methods=['POST'])
@login_required
def deactivate_device(device_id):
    """Deactivate a device"""
    try:
        device = DeviceAccess.query.get_or_404(device_id)
        device.is_active = False
        db.session.commit()

        flash('Device deactivated successfully!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error deactivating device: {str(e)}', 'error')

    return redirect(url_for('devices_list'))


# ==================
# ROUTES - Client Management (Production-Level)
# ==================


@app.route('/admin/clients')
@login_required
@permission_required('can_manage_clients')
def clients_list():
    """List all clients with search/filter/pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    sort_by = request.args.get('sort', 'created_at')

    query = Client.query

    # Search filter
    if search:
        query = query.filter(
            db.or_(
                Client.name.ilike(f'%{search}%'),
                Client.contact_person.ilike(f'%{search}%'),
                Client.email.ilike(f'%{search}%'),
                Client.phone.ilike(f'%{search}%'),
                Client.gst_number.ilike(f'%{search}%')
            )
        )

    # Status filter
    if status:
        query = query.filter_by(status=status)

    # Sorting
    if sort_by == 'name':
        query = query.order_by(Client.name)
    elif sort_by == 'licenses':
        # Sort by license count - needs subquery
        query = query.order_by(Client.created_at.desc())
    else:
        query = query.order_by(Client.created_at.desc())

    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    clients = pagination.items

    # Statistics
    total_clients = Client.query.count()
    active_clients = Client.query.filter_by(status='active').count()

    return render_template(
        'clients.html',
        clients=clients,
        pagination=pagination,
        search=search,
        status=status,
        sort_by=sort_by,
        total_clients=total_clients,
        active_clients=active_clients
    )


@app.route('/admin/clients/add', methods=['POST'])
@login_required
@permission_required('can_manage_clients')
def add_client():
    """Add new client"""
    try:
        data = request.form

        # Validation
        if not data.get('name'):
            flash('✗ Company name is required!', 'error')
            return redirect(url_for('clients_list'))

        # Check duplicate
        if Client.query.filter_by(name=data['name']).first():
            flash(f'✗ Client "{data["name"]}" already exists!', 'error')
            return redirect(url_for('clients_list'))

        client = Client(
            name=data['name'],
            contact_person=data.get('contact_person'),
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            gst_number=data.get('gst_number'),
            notes=data.get('notes'),
            status='active'
        )
        db.session.add(client)
        db.session.commit()

        # Log activity for GTMS side (already there)
        log = ActivityLog(
            action='client_created',
            details=f'Created client: {client.name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)

        # NEW: log admin action
        admin_log = AdminActivityLog(
            admin_id=session.get('admin_id'),
            action='client_created',
            details=f'Created client: {client.name}',
            ip_address=request.remote_addr
        )
        db.session.add(admin_log)

        db.session.commit()

        flash(f'✓ Client "{client.name}" created successfully!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'✗ Error creating client: {str(e)}', 'error')

    return redirect(url_for('clients_list'))


@app.route('/admin/clients/edit/<int:client_id>', methods=['POST'])
@login_required
@permission_required('can_manage_clients')
def edit_client(client_id):
    """Edit existing client"""
    try:
        client = Client.query.get_or_404(client_id)
        data = request.form

        old_name = client.name
        client.name = data.get('name', client.name)
        client.contact_person = data.get('contact_person', client.contact_person)
        client.email = data.get('email', client.email)
        client.phone = data.get('phone', client.phone)
        client.address = data.get('address', client.address)
        client.gst_number = data.get('gst_number', client.gst_number)
        client.status = data.get('status', client.status)
        client.notes = data.get('notes', client.notes)

        db.session.commit()

        # Log activity
        log = ActivityLog(
            action='client_updated',
            details=f'Updated client: {old_name} → {client.name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        flash(f'✓ Client "{client.name}" updated successfully!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'✗ Error updating client: {str(e)}', 'error')

    return redirect(url_for('clients_list'))


@app.route('/admin/clients/delete/<int:client_id>', methods=['POST'])
@login_required
@permission_required('can_manage_clients')
def delete_client(client_id):
    """Delete client (only if no licenses)"""
    try:
        client = Client.query.get_or_404(client_id)

        # Check if client has any licenses (active or inactive)
        total_licenses = License.query.filter_by(client_id=client.id).count()

        if total_licenses > 0:
            flash(
                f'✗ Cannot delete client "{client.name}". '
                f'Has {total_licenses} license(s) linked. Deactivate client instead.',
                'error'
            )
            return redirect(url_for('clients_list'))

        client_name = client.name
        db.session.delete(client)

        # Log activity
        log = ActivityLog(
            action='client_deleted',
            details=f'Deleted client: {client_name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        flash(f'✓ Client "{client_name}" deleted successfully!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'✗ Error deleting client: {str(e)}', 'error')

    return redirect(url_for('clients_list'))


@app.route('/admin/clients/toggle-status/<int:client_id>/<status>', methods=['POST'])
@login_required
@permission_required('can_manage_clients')
def toggle_client_status(client_id, status):
    """Toggle client status (active/inactive)"""
    try:
        client = Client.query.get_or_404(client_id)
        old_status = client.status
        client.status = status
        db.session.commit()

        # Log activity
        log = ActivityLog(
            action='client_status_changed',
            details=f'Client "{client.name}" status: {old_status} → {status}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({'success': True, 'message': f'Client status changed to {status}'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/clients/view/<int:client_id>')
@login_required
@permission_required('can_manage_clients')
def view_client(client_id):
    """View client details with licenses and statistics"""
    client = Client.query.get_or_404(client_id)
    licenses = License.query.filter_by(client_id=client.id).order_by(License.created_at.desc()).all()

    # Calculate statistics
    total_licenses = len(licenses)
    active_licenses = sum(1 for lic in licenses if lic.is_active)
    expired_licenses = sum(
        1 for lic in licenses if lic.expiry_date < datetime.utcnow() and lic.is_active
    )

    total_users = sum(len(lic.users) for lic in licenses)
    total_devices = sum(len([d for d in lic.devices if d.is_active]) for lic in licenses)

    return render_template(
        'client_detail.html',
        client=client,
        licenses=licenses,
        total_licenses=total_licenses,
        active_licenses=active_licenses,
        expired_licenses=expired_licenses,
        total_users=total_users,
        total_devices=total_devices,
        now=datetime.utcnow()
    )


@app.route('/admin/clients/export')
@login_required
@permission_required('can_manage_clients')
def export_clients():
    """Export clients to CSV"""
    import csv
    from io import StringIO
    from flask import make_response

    clients = Client.query.order_by(Client.created_at.desc()).all()

    si = StringIO()
    writer = csv.writer(si)

    # Header
    writer.writerow([
        'ID', 'Company Name', 'Contact Person', 'Email', 'Phone',
        'GST Number', 'Address', 'Status', 'Total Licenses', 'Created Date'
    ])

    # Data
    for c in clients:
        writer.writerow([
            c.id,
            c.name,
            c.contact_person or '',
            c.email or '',
            c.phone or '',
            c.gst_number or '',
            c.address or '',
            c.status,
            len(c.licenses),
            c.created_at.strftime('%Y-%m-%d %H:%M')
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=clients_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output


# ==================
# ROUTES - Subscription Management
# ==================


@app.route('/admin/subscriptions')
@login_required
@permission_required('can_manage_payments')
def subscriptions_list():
    """List all subscriptions"""
    subscriptions = Subscription.query.order_by(Subscription.created_at.desc()).all()

    # Stats
    total_subs = Subscription.query.count()
    active_subs = Subscription.query.filter_by(status='active').count()
    expired_subs = Subscription.query.filter_by(status='expired').count()

    # Calculate MRR (Monthly Recurring Revenue)
    monthly_revenue = db.session.query(db.func.sum(Subscription.amount)).filter(
        Subscription.status == 'active',
        Subscription.plan_type == 'monthly'
    ).scalar() or 0

    clients = Client.query.order_by(Client.name).all()

    return render_template(
        'subscriptions.html',
        subscriptions=subscriptions,
        total_subs=total_subs,
        active_subs=active_subs,
        expired_subs=expired_subs,
        monthly_revenue=monthly_revenue,
        clients=clients
    )


@app.route('/admin/subscriptions/add', methods=['POST'])
@login_required
@permission_required('can_manage_payments')
def add_subscription():
    """Add new subscription"""
    try:
        data = request.form

        client_id = int(data['client_id'])
        plan_type = data['plan_type']
        amount = float(data['amount'])

        # Calculate end date
        start_date = datetime.utcnow()
        if plan_type == 'monthly':
            end_date = start_date + timedelta(days=30)
        elif plan_type == 'quarterly':
            end_date = start_date + timedelta(days=90)
        elif plan_type == 'yearly':
            end_date = start_date + timedelta(days=365)
        else:  # lifetime
            end_date = start_date + timedelta(days=36500)

        subscription = Subscription(
            client_id=client_id,
            license_id=data.get('license_id') or None,
            plan_name=data['plan_name'],
            plan_type=plan_type,
            amount=amount,
            start_date=start_date,
            end_date=end_date,
            notes=data.get('notes')
        )

        db.session.add(subscription)
        db.session.commit()

        flash(f'✓ Subscription created for {subscription.client.name}!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'✗ Error creating subscription: {str(e)}', 'error')

    return redirect(url_for('subscriptions_list'))


# ==================
# ROUTES - Payment Management
# ==================


@app.route('/admin/payments')
@login_required
@permission_required('can_manage_payments')
def payments_list():
    """List all payments"""
    payments = Payment.query.order_by(Payment.payment_date.desc()).all()

    # Stats
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='completed').scalar() or 0
    total_payments = Payment.query.filter_by(status='completed').count()
    pending_payments = Payment.query.filter_by(status='pending').count()

    # This month revenue
    first_day = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == 'completed',
        Payment.payment_date >= first_day
    ).scalar() or 0

    clients = Client.query.order_by(Client.name).all()

    return render_template(
        'payments.html',
        payments=payments,
        total_revenue=total_revenue,
        total_payments=total_payments,
        pending_payments=pending_payments,
        month_revenue=month_revenue,
        clients=clients
    )


@app.route('/admin/payments/add', methods=['POST'])
@login_required
@permission_required('can_manage_payments')
def add_payment():
    """Add new payment"""
    try:
        data = request.form

        # Generate invoice number
        last_invoice = Payment.query.order_by(Payment.id.desc()).first()
        invoice_num = f"INV-{datetime.now().year}-{(last_invoice.id + 1) if last_invoice else 1:04d}"

        payment = Payment(
            client_id=int(data['client_id']),
            subscription_id=data.get('subscription_id') or None,
            license_id=data.get('license_id') or None,
            amount=float(data['amount']),
            currency=data.get('currency', 'INR'),
            payment_method=data['payment_method'],
            transaction_id=data.get('transaction_id'),
            payment_date=datetime.utcnow(),
            payment_for=data['payment_for'],
            invoice_number=invoice_num,
            invoice_generated=False,
            invoice_path=None,
            status=data.get('status', 'completed'),
            created_at=datetime.utcnow(),
            created_by=session.get('admin_username'),
            notes=data.get('notes')
        )

        db.session.add(payment)
        db.session.commit()

        flash(f'✓ Payment recorded! Invoice: {invoice_num}', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'✗ Error recording payment: {str(e)}', 'error')

    return redirect(url_for('payments_list'))


@app.route('/admin/payments/generate-invoice/<int:payment_id>')
@login_required
@permission_required('can_manage_payments')
def generate_invoice(payment_id):
    """Generate PDF invoice for payment"""
    try:
        from utils.invoice_generator import InvoiceGenerator

        payment = Payment.query.get_or_404(payment_id)

        # ✅ Block invoice generation for pending payments
        if payment.status != 'completed':
            flash('Cannot generate invoice for pending payment.', 'error')
            return redirect(url_for('payments_list'))

        client = Client.query.get(payment.client_id)

        # Prepare invoice data
        invoice_data = {
            'invoice_number': payment.invoice_number,
            'invoice_date': payment.payment_date,
            'due_date': payment.payment_date,
            'company': {
                'name': 'Your Company Name Pvt Ltd',
                'address': 'Address Line 1\nCity, State - 400001',
                'email': 'info@yourcompany.com',
                'phone': '+91-9876543210',
                'gst': '27AAAAA0000A1Z5'
            },
            'client': {
                'name': client.name,
                'contact': client.contact_person,
                'address': client.address or '-',
                'email': client.email,
                'phone': client.phone,
                'gst': client.gst_number
            },
            'items': [
                {
                    'description': payment.payment_for,
                    'quantity': 1,
                    'rate': payment.amount / 1.18,
                    'amount': payment.amount / 1.18
                }
            ],
            'subtotal': payment.amount / 1.18,
            'tax_rate': 18,
            'tax_amount': payment.amount - (payment.amount / 1.18),
            'discount': 0,
            'total': payment.amount,
            'payment_method': payment.payment_method,
            'transaction_id': payment.transaction_id,
            'notes': 'Thank you for your business!'
        }

        generator = InvoiceGenerator()
        pdf_path = generator.generate_invoice(invoice_data)

        # Update payment record
        payment.invoice_generated = True
        payment.invoice_path = pdf_path
        db.session.commit()

        from flask import send_file
        return send_file(pdf_path, as_attachment=True, download_name=f'{payment.invoice_number}.pdf')

    except Exception as e:
        flash(f'✗ Error generating invoice: {str(e)}', 'error')
        return redirect(url_for('payments_list'))


# ==================
# ROUTES - License Management
# ==================


@app.route('/admin/licenses')
@login_required
@permission_required('can_manage_licenses')
def licenses_list():
    product_filter = request.args.get('product', 'all')
    
    query = License.query
    if product_filter != 'all':
        query = query.filter_by(product_name=product_filter)
    
    licenses = query.order_by(License.created_at.desc()).all()
    
    # Get unique products from existing licenses
    products = db.session.query(License.product_name.distinct()).filter(License.product_name.isnot(None)).all()
    products = [p[0] for p in products]
    
    clients = Client.query.order_by(Client.name).all()
    
    return render_template('licenses.html', licenses=licenses, products=products, 
                          clients=clients, now=datetime.utcnow(), product_filter=product_filter)




@app.route('/admin/licenses/add', methods=['POST'])
@login_required
@permission_required('can_manage_licenses')
def add_license():
    try:
        data = request.form
        
        license_key = f"GTMS-{secrets.token_hex(8).upper()}"

        subscription_type = data.get('subscription_type', 'yearly')
        if subscription_type == 'monthly':
            expiry_date = datetime.utcnow() + timedelta(days=30)
        elif subscription_type == 'yearly':
            expiry_date = datetime.utcnow() + timedelta(days=365)
        else:
            expiry_date = datetime.utcnow() + timedelta(days=36500)

        # ✅ simple product name string
        product_name = data.get('product_name', 'GTMS')

        license = License(
            license_key=license_key,
            company_name=data['company_name'],
            client_id=data.get('client_id') or None,
            product_name=product_name,  # ✅ use string field
            max_users=int(data.get('max_users', 5)),
            max_devices=int(data.get('max_devices', 3)),
            plan_type=data.get('plan_type', 'Standard'),
            subscription_type=subscription_type,
            expiry_date=expiry_date,
            contact_email=data.get('contact_email'),
            contact_phone=data.get('contact_phone'),
            notes=data.get('notes')
        )

        db.session.add(license)
        db.session.commit()
        flash(f'License {license_key} created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating license: {str(e)}', 'error')
    
    return redirect(url_for('licenses_list'))





# ==================
# API - License Verification (for GTMS Desktop App)
# ==================

@app.route('/api/verify-license', methods=['POST'])
def verify_license_api():
    """Verify license key and hardware ID - used by GTMS app"""
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        hardware_id = data.get('hardware_id')
        
        if not license_key or not hardware_id:
            return jsonify({'valid': False, 'message': 'Missing license key or hardware ID'}), 400
        
        # Find license
        license = License.query.filter_by(license_key=license_key).first()
        
        if not license:
            return jsonify({'valid': False, 'message': 'Invalid license key'}), 404
        
        if not license.is_active:
            return jsonify({'valid': False, 'message': 'License has been deactivated'}), 403
        
        if license.expiry_date < datetime.utcnow():
            return jsonify({'valid': False, 'message': 'License has expired'}), 403
        
        # Check/register device
        device = DeviceAccess.query.filter_by(license_id=license.id, hardware_id=hardware_id).first()
        
        if device:
            device.last_access = datetime.utcnow()
            device.access_count += 1
            device.is_active = True
        else:
            # Check device limit
            active_devices = DeviceAccess.query.filter_by(license_id=license.id, is_active=True).count()
            if active_devices >= license.max_devices:
                return jsonify({'valid': False, 'message': f'Device limit reached ({license.max_devices} max)'}), 403
            
            device = DeviceAccess(
                license_id=license.id,
                hardware_id=hardware_id,
                ip_address=request.remote_addr
            )
            db.session.add(device)
        
        db.session.commit()
        
        days_remaining = (license.expiry_date - datetime.utcnow()).days
        
        return jsonify({
            'valid': True,
            'license_key': license.license_key,
            'customer_name': license.company_name,
            'customer_email': license.contact_email or '',
            'plan_type': license.plan_type,
            'subscription_type': license.subscription_type,
            'expiry_date': license.expiry_date.isoformat(),
            'activation_date': license.activation_date.isoformat(),
            'days_remaining': days_remaining,
            'hardware_id': hardware_id,
            'verification_count': device.access_count
        })
        
    except Exception as e:
        return jsonify({'valid': False, 'message': str(e)}), 500


@app.route('/api/activate-license', methods=['POST'])
def activate_license_api():
    """Activate license - same as verify"""
    return verify_license_api()


@app.route('/api/deactivate-license', methods=['POST'])
def deactivate_license_api():
    """Deactivate license on specific hardware"""
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        hardware_id = data.get('hardware_id')
        
        if license_key and hardware_id:
            license = License.query.filter_by(license_key=license_key).first()
            if license:
                device = DeviceAccess.query.filter_by(license_id=license.id, hardware_id=hardware_id).first()
                if device:
                    device.is_active = False
                    db.session.commit()
        
        return jsonify({'success': True, 'message': 'License deactivated'})
    except:
        return jsonify({'success': False, 'message': 'Deactivation failed'}), 500


# ==================
# API - GTMS User Login (NEW!)
# ==================

@app.route('/api/login', methods=['POST'])
def api_login():
    """
    ✅ NEW API endpoint for GTMS user login
    Returns user data if credentials are valid
    """
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'}), 400
        
        # Hash password with SHA-256
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Find user in GTMSUser table
        user = GTMSUser.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Check password
        if user.password_hash != password_hash:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Check if user is active
        if not user.is_active:
            return jsonify({'success': False, 'message': 'Account is disabled'}), 403
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        # Log activity
        log = ActivityLog(
            user_id=user.id,
            action='login',
            details=f'API login from {request.remote_addr}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        # Return user data
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role,
                'email': user.email or '',
                'phone': user.phone or '',
                'company_name': user.company_name or ''
            }
        })
        
    except Exception as e:
        print(f"Login API Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================
# API - User Login Validation (OLD - for backward compatibility)
# ==================

@app.route('/api/validate', methods=['POST'])
def validate_login():
    """Validate user login from GTMS application (with license check)"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        hardware_id = data.get('hardware_id')
        
        user = GTMSUser.query.filter_by(username=username).first()
        
        if not user or not user.is_active:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user.password_hash != password_hash:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        if not user.license or not user.license.is_active:
            return jsonify({'success': False, 'message': 'No active license'}), 403
        
        if user.license.expiry_date < datetime.utcnow():
            return jsonify({'success': False, 'message': 'License expired'}), 403
        
        active_devices = DeviceAccess.query.filter_by(license_id=user.license_id, is_active=True).count()
        
        device = DeviceAccess.query.filter_by(user_id=user.id, hardware_id=hardware_id).first()
        
        if device:
            device.last_access = datetime.utcnow()
            device.access_count += 1
            device.is_active = True
        else:
            if active_devices >= user.license.max_devices:
                return jsonify({'success': False, 'message': f'Device limit reached ({user.license.max_devices} max)'}), 403
            
            device = DeviceAccess(
                user_id=user.id,
                license_id=user.license_id,
                hardware_id=hardware_id,
                ip_address=request.remote_addr
            )
            db.session.add(device)
        
        user.last_login = datetime.utcnow()
        
        log = ActivityLog(
            user_id=user.id,
            action='login',
            details=f'Login from {hardware_id[:10]}...',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role,
                'email': user.email
            },
            'license': {
                'license_key': user.license.license_key,
                'plan_type': user.license.plan_type,
                'expiry_date': user.license.expiry_date.isoformat(),
                'days_remaining': (user.license.expiry_date - datetime.utcnow()).days
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================
# Initialization
# ==================

def init_db():
    """Initialize database"""
    with app.app_context():
        db.create_all()
        
        if not AdminUser.query.filter_by(username='admin').first():
            admin = AdminUser(username='admin', email='admin@gtms.com')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin created: admin / admin123")


if __name__ == '__main__':
    os.makedirs('database', exist_ok=True)
    init_db()
    
    print("=" * 60)
    print("🚀 GTMS License Server Starting...")
    print("=" * 60)
    print("📍 Admin Panel: http://localhost:5000/admin/login")
    print("👤 Login: admin / admin123")
    print("\n📡 API Endpoints:")
    print("   • /api/verify-license (License verification)")
    print("   • /api/activate-license (License activation)")
    print("   • /api/deactivate-license (License deactivation)")
    print("   • /api/login (User authentication) ✨ NEW")
    print("   • /api/validate (User login with license check)")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
