# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database Configuration - Render PostgreSQL (uses environment variables only)
    # The actual connection string should be in your .env file with ?sslmode=require
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'postgresql://localhost:5432/your_database'  # Placeholder only - use .env
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database engine options for PostgreSQL (works for both Render and local)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'sslmode': os.environ.get('DB_SSL_MODE', 'require'),  # Render requires 'require'
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
    
    @staticmethod
    def validate_config(config_dict):
        """Validate required configuration from a config dictionary"""
        required = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_ADMIN_RECIPIENT']
        missing = []
        
        for req in required:
            if not config_dict.get(req):
                missing.append(req)
        
        if missing:
            print(f"❌ Configuration Error: Missing required environment variables: {', '.join(missing)}")
            print("Please check your .env file and ensure all required variables are set.")
            return False
        
        print("✅ Configuration validated successfully")
        return True


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    # Use Render PostgreSQL or local database from .env
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DEV_DATABASE_URL',
        os.environ.get('DATABASE_URL', 'postgresql://localhost:5432/joztembo_dev')
    )
    
    # More verbose logging in development
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        'echo': False,  # Set to True to see SQL queries
    }


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # Use Render PostgreSQL from environment variable
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://localhost:5432/your_database'  # Fallback - should be set in Render env vars
    )
    
    # Optimized for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        'pool_size': 20,
        'max_overflow': 40,
    }


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}