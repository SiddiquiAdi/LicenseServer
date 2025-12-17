from app import app, db, AdminUser

username = "admin"
password = "Admin@123"

with app.app_context():
    admin = AdminUser.query.filter_by(username=username).first()
    
    if not admin:
        print(f"❌ No user found with username='{username}'")
    else:
        print(f"✓ Found user: {admin.username} (ID={admin.id})")
        print(f"  Role: {admin.role}")
        print(f"  Active: {admin.is_active}")
        print(f"  password_hash: {admin.password_hash[:60]}...")
        
        # Test password check
        is_valid = admin.check_password(password)
        print(f"\n  Testing password '{password}': {'✓ VALID' if is_valid else '❌ INVALID'}")
        
        if not is_valid:
            print("\n  The password hash in database does not match.")
            print("  Re-setting password now...")
            admin.set_password(password)
            db.session.commit()
            print("  ✓ Password reset. Try logging in again.")
