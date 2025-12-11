import sqlite3
from datetime import datetime, timedelta
import secrets
import hashlib

class Database:
    def __init__(self, db_path='license_server.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Licenses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                product_name TEXT DEFAULT 'GTMS',
                subscription_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                hardware_id TEXT,
                is_active INTEGER DEFAULT 1,
                max_activations INTEGER DEFAULT 1,
                current_activations INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_validated TEXT
            )
        ''')
        
        # Activation logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT NOT NULL,
                hardware_id TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                ip_address TEXT,
                FOREIGN KEY (license_key) REFERENCES licenses (license_key)
            )
        ''')
        
        # Admin users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_license_key(self):
        """Generate unique license key"""
        return '-'.join([secrets.token_hex(4).upper() for _ in range(4)])
    
    def create_license(self, customer_name, customer_email, subscription_type, product_name='GTMS'):
        """Create new license"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        license_key = self.generate_license_key()
        start_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Calculate expiry based on subscription type
        if subscription_type == '1_month':
            expiry = datetime.now() + timedelta(days=30)
        elif subscription_type == '3_months':
            expiry = datetime.now() + timedelta(days=90)
        elif subscription_type == '6_months':
            expiry = datetime.now() + timedelta(days=180)
        elif subscription_type == '1_year':
            expiry = datetime.now() + timedelta(days=365)
        else:
            expiry = datetime.now() + timedelta(days=30)
        
        expiry_date = expiry.strftime('%Y-%m-%d %H:%M:%S')
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO licenses (license_key, customer_name, customer_email, product_name,
                                subscription_type, start_date, expiry_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (license_key, customer_name, customer_email, product_name,
              subscription_type, start_date, expiry_date, created_at))
        
        conn.commit()
        conn.close()
        
        return license_key
    
    def validate_license(self, license_key, hardware_id):
        """Validate license and activate if needed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM licenses WHERE license_key = ?', (license_key,))
        license_data = cursor.fetchone()
        
        if not license_data:
            conn.close()
            return {'valid': False, 'message': 'Invalid license key'}
        
        # Parse license data
        cols = ['id', 'license_key', 'customer_name', 'customer_email', 'product_name',
                'subscription_type', 'start_date', 'expiry_date', 'hardware_id',
                'is_active', 'max_activations', 'current_activations', 'created_at', 'last_validated']
        license = dict(zip(cols, license_data))
        
        # Check if license is active
        if not license['is_active']:
            conn.close()
            return {'valid': False, 'message': 'License has been deactivated. Contact developer.'}
        
        # Check expiry
        expiry_date = datetime.strptime(license['expiry_date'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() > expiry_date:
            conn.close()
            return {'valid': False, 'message': 'Subscription expired. Contact developer.'}
        
        # Check hardware ID binding
        if license['hardware_id'] is None:
            # First activation
            cursor.execute('''
                UPDATE licenses 
                SET hardware_id = ?, current_activations = 1, last_validated = ?
                WHERE license_key = ?
            ''', (hardware_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), license_key))
            
            cursor.execute('''
                INSERT INTO activation_logs (license_key, hardware_id, action, timestamp)
                VALUES (?, ?, 'FIRST_ACTIVATION', ?)
            ''', (license_key, hardware_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            
            days_left = (expiry_date - datetime.now()).days
            return {
                'valid': True,
                'message': 'License activated successfully',
                'customer_name': license['customer_name'],
                'expiry_date': license['expiry_date'],
                'days_remaining': days_left
            }
        
        elif license['hardware_id'] == hardware_id:
            # Valid hardware ID
            cursor.execute('''
                UPDATE licenses SET last_validated = ? WHERE license_key = ?
            ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), license_key))
            conn.commit()
            conn.close()
            
            days_left = (expiry_date - datetime.now()).days
            return {
                'valid': True,
                'message': 'License valid',
                'customer_name': license['customer_name'],
                'expiry_date': license['expiry_date'],
                'days_remaining': days_left
            }
        else:
            # Hardware ID mismatch
            conn.close()
            return {'valid': False, 'message': 'License already activated on another machine'}
    
    def get_all_licenses(self):
        """Get all licenses"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM licenses ORDER BY created_at DESC')
        licenses = cursor.fetchall()
        conn.close()
        return licenses
    
    def update_license_status(self, license_key, is_active):
        """Activate or deactivate license"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE licenses SET is_active = ? WHERE license_key = ?',
                      (is_active, license_key))
        conn.commit()
        conn.close()
    
    def extend_license(self, license_key, days):
        """Extend license expiry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT expiry_date FROM licenses WHERE license_key = ?', (license_key,))
        result = cursor.fetchone()
        
        if result:
            current_expiry = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
            new_expiry = current_expiry + timedelta(days=days)
            
            cursor.execute('UPDATE licenses SET expiry_date = ? WHERE license_key = ?',
                          (new_expiry.strftime('%Y-%m-%d %H:%M:%S'), license_key))
            conn.commit()
        
        conn.close()
    
    def create_admin(self, username, password, email):
        """Create admin user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute('''
                INSERT INTO admin_users (username, password_hash, email, created_at)
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, email, created_at))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def verify_admin(self, username, password):
        """Verify admin credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute('''
            SELECT * FROM admin_users WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
