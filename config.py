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



    # add these mail settings INSIDE the class, uppercase
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = "siddiquiadi249@gmail.com"
    MAIL_PASSWORD = "spixgevbzvdxzwva"   # no spaces
    MAIL_DEFAULT_SENDER = "siddiquiadi249@gmail.com"

