import os
from dotenv import load_dotenv

# Load environment variables from .env file
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

def get_env_bool(key, default=False):
    """Get boolean value from environment variable"""
    value = os.environ.get(key, str(default))
    return value.lower() in ('true', '1', 'yes', 'on')

class Config:
    """Base configuration"""
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database Configuration
    _database_url = format_database_url(os.environ.get('DATABASE_URL'))
    SQLALCHEMY_DATABASE_URI = _database_url or 'postgresql://localhost:5432/joztembo_dev'
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
    MAIL_USE_TLS = get_env_bool('MAIL_USE_TLS', True)
    MAIL_USE_SSL = get_env_bool('MAIL_USE_SSL', False)
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
    
    # Use DEV_DATABASE_URL if available, otherwise fallback to DATABASE_URL or local
    _dev_db_url = os.environ.get('DEV_DATABASE_URL') or os.environ.get('DATABASE_URL')
    SQLALCHEMY_DATABASE_URI = format_database_url(_dev_db_url) or 'postgresql://localhost:5432/joztembo_dev'
    
    # Enable SQL query logging for debugging
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        'echo': True,
    }
    
    # Development-specific settings
    MAIL_SUPPRESS_SEND = get_env_bool('MAIL_SUPPRESS_SEND', False)
    MAIL_DEBUG = True


class ProductionConfig(Config):
    """Production configuration for LIVE WEBSITE on Render"""
    DEBUG = False
    
    # Get database URL from environment (MUST be set in Render)
    _prod_db_url = format_database_url(os.environ.get('DATABASE_URL'))
    
    if not _prod_db_url:
        # Only raise error if we're actually in production
        if os.environ.get('RENDER') or os.environ.get('FLASK_ENV') == 'production':
            raise ValueError("❌ DATABASE_URL environment variable is required in production!")
        else:
            # Fallback for local testing with ProductionConfig
            print("⚠️  Warning: DATABASE_URL not set. Using local fallback.")
            _prod_db_url = 'postgresql://localhost:5432/joztembo_prod'
    
    SQLALCHEMY_DATABASE_URI = _prod_db_url
    
    # Optimized for production performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        'pool_size': 20,
        'max_overflow': 40,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # Production mail settings
    MAIL_DEBUG = False
    MAIL_SUPPRESS_SEND = False
    
    # Security settings for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True


class TestingConfig(Config):
    """Testing configuration - for running tests only"""
    TESTING = True
    DEBUG = True
    
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable email for testing
    MAIL_SUPPRESS_SEND = True
    MAIL_DEBUG = False
    
    # Simplified engine options for testing
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},
    }
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get the appropriate configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, DevelopmentConfig)

# For backward compatibility
DevelopmentConfig  # Keep these available
ProductionConfig
TestingConfig