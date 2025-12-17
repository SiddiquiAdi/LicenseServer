from app import app, db, AdminUser
from werkzeug.security import generate_password_hash

print("🔧 Fixing admin user...")

with app.app_context():
    # Get or create admin
    admin = AdminUser.query.filter_by(username='admin').first()
    if not admin:
        admin = AdminUser(username='admin', email='admin@example.com')
        db.session.add(admin)
    
    # Force set hashed password
    hashed_pw = generate_password_hash('Admin@123')
    admin.password_hash = hashed_pw
    admin.role = 'SuperAdmin'
    admin.is_active = True
    admin.can_manage_clients = True
    admin.can_manage_licenses = True
    admin.can_manage_payments = True
    admin.can_manage_users = True
    
    db.session.commit()
    
    # Verify
    db.session.refresh(admin)
    print(f"✅ FIXED!")
    print(f"   Username: admin")
    print(f"   Password: Admin@123")
    print(f"   Hash: {admin.password_hash[:60]}...")
    print(f"   check_password: {admin.check_password('Admin@123')}")
    print(f"   All permissions: {all([admin.can_manage_clients, admin.can_manage_licenses, admin.can_manage_payments, admin.can_manage_users])}")
