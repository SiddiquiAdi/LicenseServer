from app import app, db, AdminUser

NEW_PASSWORD = "Test@123"  # Change this

with app.app_context():
    admin = AdminUser.query.filter_by(username='admin').first()
    if admin:
        admin.set_password(NEW_PASSWORD)
        db.session.commit()
        print(f"✅ Password changed to: {NEW_PASSWORD}")
        print(f"   New hash: {admin.password_hash[:60]}...")
    else:
        print("❌ No admin user found")
