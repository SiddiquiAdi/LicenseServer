import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-super-secret-key-change-in-production')

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql+psycopg2://gtms_user:Adi111@localhost:5432/gtms_license'
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'admin123'

    APP_NAME = 'GTMS License Server'
    APP_VERSION = '1.0.0'
