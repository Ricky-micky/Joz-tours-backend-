import os
from dotenv import load_dotenv

load_dotenv()

def format_database_url(url):
    """Safely formats the database URL for SQLAlchemy and adds SSL mode if missing."""
    if not url:
        return None
    
    # SQLAlchemy requires 'postgresql://' instead of 'postgres://'
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
        
    # Safely append sslmode depending on whether query parameters exist
    if 'sslmode=' not in url:
        if '?' in url:
            url += '&sslmode=require'
        else:
            url += '?sslmode=require'
            
    return url

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database Configuration - Render / Supabase PostgreSQL
    database_url = format_database_url(os.environ.get('DATABASE_URL'))
    
    if database_url:
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Fallback for local development only
        SQLALCHEMY_DATABASE_URI = 'postgresql://localhost:5432/joztembo_dev'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database engine options for PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'connect_timeout': 10,
        },
        'pool_size': 10,
        'max_overflow': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # Flask-Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME', 'noreply@example.com'))
    MAIL_ADMIN_RECIPIENT = os.environ.get('MAIL_ADMIN_RECIPIENT')
    
    # App configuration
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    """Development configuration for local testing"""
    DEBUG = True
    
    dev_db_url = format_database_url(os.environ.get('DEV_DATABASE_URL') or os.environ.get('DATABASE_URL'))
    
    if dev_db_url:
        SQLALCHEMY_DATABASE_URI = dev_db_url
    else:
        SQLALCHEMY_DATABASE_URI = 'postgresql://localhost:5432/joztembo_dev'
    
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        'echo': True,  # Shows SQL queries in terminal for debugging
    }


class ProductionConfig(Config):
    """Production configuration for LIVE WEBSITE on Render"""
    DEBUG = False
    
    # Get database URL from environment (MUST be set in Render)
    production_db_url = format_database_url(os.environ.get('DATABASE_URL'))
    
    if not production_db_url:
        raise ValueError("❌ DATABASE_URL environment variable is required in production!")
    
    SQLALCHEMY_DATABASE_URI = production_db_url
    
    # Optimized for production performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        'pool_size': 20,
        'max_overflow': 40,
    }


class TestingConfig(Config):
    """Testing configuration - for running tests only"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}