# app.py - COMPLETE WORKING VERSION WITH ALL ROUTES (INCLUDING USER CRUD SYSTEM)
from flask import Flask, request, jsonify, g
from flask_mail import Mail, Message
from flask_cors import CORS
from datetime import datetime, UTC, timedelta
from functools import wraps
import os
import logging
import re
import jwt
from logging.handlers import RotatingFileHandler

# Import config and extensions
from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from extensions import db, migrate

# Import models
from models import (
    User, Comment, Lodge, LodgePrice, PriceHistory, Story, Review, 
    AdminActionLog, SafariPackage, PackageDay, PackageItinerary, 
    ItineraryAccommodation, PackagePrice, SafariReview, SafariComment, Park,
    CustomerReview, ReviewReply
)

def create_app(config_class=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    if config_class:
        app.config.from_object(config_class)
    else:
        env = os.environ.get('FLASK_ENV', 'development')
        if env == 'production':
            app.config.from_object(ProductionConfig)
        elif env == 'testing':
            app.config.from_object(TestingConfig)
        else:
            app.config.from_object(DevelopmentConfig)
    
    # Ensure SECRET_KEY is set for JWT
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', app.config.get('SECRET_KEY', 'your-secret-key-change-in-production'))
    
    # JWT Configuration
    app.config['JWT_EXPIRATION_HOURS'] = 168  # 7 days
    
    # Override with environment variables if they exist
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', app.config.get('MAIL_SERVER', 'smtp.gmail.com'))
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', app.config.get('MAIL_PORT', 587)))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', app.config.get('MAIL_USERNAME'))
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', app.config.get('MAIL_PASSWORD'))
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME'))
    app.config['MAIL_ADMIN_RECIPIENT'] = os.environ.get('MAIL_ADMIN_RECIPIENT', app.config.get('MAIL_ADMIN_RECIPIENT'))
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    mail = Mail(app)
    
    # Setup logging
    setup_logging(app)
    
    # Register routes
    register_routes(app, mail)
    
    # Create database tables on app startup (for production)
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database tables created/verified successfully")
        except Exception as e:
            app.logger.error(f"Database initialization error: {e}")
    
    return app

def setup_logging(app):
    """Configure logging"""
    if not app.debug or os.environ.get('ENABLE_LOGGING', 'False').lower() == 'true':
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/safari_booking.log', 
            maxBytes=10240, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Safari Booking System startup')

# ============ AUTH DECORATORS ============

def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user = User.verify_auth_token(token)
        if not user:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        
        # Check if user is active
        if not user.is_active:
            return jsonify({'success': False, 'error': 'Account has been deactivated'}), 403
        
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user = User.verify_auth_token(token)
        if not user or not user.is_admin:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        if not user.is_active:
            return jsonify({'success': False, 'error': 'Account has been deactivated'}), 403
        
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def optional_auth(f):
    """Decorator for optional authentication - sets g.current_user if token is valid"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        g.current_user = None
        if token:
            user = User.verify_auth_token(token)
            if user and user.is_active:
                g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def register_routes(app, mail):
    """Register all routes"""
    
    # ============ EMAIL HELPER FUNCTIONS ============
    def send_admin_email(booking_data):
        """Send booking notification to admin"""
        try:
            booking_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            is_safari = booking_data.get('park') and 'National' in str(booking_data.get('park', ''))
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .field {{ margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
                    .label {{ font-weight: bold; color: #495057; display: block; margin-bottom: 5px; }}
                    .value {{ color: #212529; }}
                    .booking-id {{ background: #e9ecef; padding: 15px; text-align: center; border-radius: 5px; margin-bottom: 20px; font-size: 16px; }}
                    .section-title {{ color: #495057; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-top: 20px; }}
                    .highlight {{ color: #667eea; font-weight: bold; }}
                    .badge {{ display: inline-block; padding: 5px 10px; border-radius: 20px; font-size: 12px; margin-right: 10px; }}
                    .badge-safari {{ background: #d4edda; color: #155724; }}
                    .badge-coastal {{ background: #d1ecf1; color: #0c5460; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin: 0;">🦁 Joztembo Tours</h1>
                        <p style="margin: 10px 0 0 0; opacity: 0.9;">New Booking Request Received</p>
                    </div>
                    <div class="content">
                        <div class="booking-id">
                            <strong>Booking Reference: <span class="highlight">{booking_id}</span></strong>
                        </div>
                        
                        <span class="badge badge-{'safari' if is_safari else 'coastal'}">{'🏕️ Safari Booking' if is_safari else '🏖️ Coastal Booking'}</span>
                        
                        <h3 class="section-title">📍 Trip Details</h3>
                        <div class="field">
                            <span class="label">Destination/Park:</span>
                            <span class="value">{booking_data.get('park', 'N/A')}</span>
                        </div>
                        <div class="field">
                            <span class="label">Accommodation:</span>
                            <span class="value">{booking_data.get('lodge', 'N/A')}</span>
                        </div>
                        <div class="field">
                            <span class="label">Duration:</span>
                            <span class="value">{booking_data.get('days', 'N/A')} days</span>
                        </div>
                        <div class="field">
                            <span class="label">Travelers:</span>
                            <span class="value">{booking_data.get('travelers', 'N/A')} { 'person' if str(booking_data.get('travelers', '1')) == '1' else 'people' }</span>
                        </div>
                        <div class="field">
                            <span class="label">Room Type:</span>
                            <span class="value">{booking_data.get('roomType', 'Standard')}</span>
                        </div>
                        <div class="field">
                            <span class="label">Check-in Date:</span>
                            <span class="value">{booking_data.get('checkIn', 'Not specified')}</span>
                        </div>
                        <div class="field">
                            <span class="label">Check-out Date:</span>
                            <span class="value">{booking_data.get('checkOut', 'Not specified')}</span>
                        </div>
                        
                        <h3 class="section-title">👤 Customer Information</h3>
                        <div class="field">
                            <span class="label">Full Name:</span>
                            <span class="value">{booking_data.get('fullName', 'N/A')}</span>
                        </div>
                        <div class="field">
                            <span class="label">Email Address:</span>
                            <span class="value"><a href="mailto:{booking_data.get('email', '')}">{booking_data.get('email', 'N/A')}</a></span>
                        </div>
                        <div class="field">
                            <span class="label">Phone Number:</span>
                            <span class="value"><a href="tel:{booking_data.get('phone', '')}">{booking_data.get('phone', 'N/A')}</a></span>
                        </div>
                        
                        <h3 class="section-title">💬 Additional Information</h3>
                        <div class="field">
                            <span class="label">Special Requests:</span>
                            <span class="value">{booking_data.get('message', 'No special requests')}</span>
                        </div>
                        
                        <div style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 5px; text-align: center;">
                            <p style="margin: 0; color: #6c757d; font-size: 14px;">
                                This booking was submitted through the Joztembo Tours website
                            </p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            =========================================
            JOZTEMBO TOURS - NEW BOOKING REQUEST
            =========================================
            
            Booking Reference: {booking_id}
            Type: {'Safari' if is_safari else 'Coastal'} Booking
            
            TRIP DETAILS:
            - Destination/Park: {booking_data.get('park', 'N/A')}
            - Accommodation: {booking_data.get('lodge', 'N/A')}
            - Duration: {booking_data.get('days', 'N/A')} days
            - Travelers: {booking_data.get('travelers', 'N/A')}
            - Room Type: {booking_data.get('roomType', 'Standard')}
            - Check-in: {booking_data.get('checkIn', 'Not specified')}
            - Check-out: {booking_data.get('checkOut', 'Not specified')}
            
            CUSTOMER INFORMATION:
            - Name: {booking_data.get('fullName', 'N/A')}
            - Email: {booking_data.get('email', 'N/A')}
            - Phone: {booking_data.get('phone', 'N/A')}
            
            SPECIAL REQUESTS:
            {booking_data.get('message', 'No special requests')}
            
            Submitted via Joztembo Tours website
            =========================================
            """
            
            admin_email = app.config.get('MAIL_ADMIN_RECIPIENT')
            if not admin_email:
                raise ValueError("Admin recipient email not configured")
            
            sender_email = app.config.get('MAIL_DEFAULT_SENDER') or app.config.get('MAIL_USERNAME')
            
            msg = Message(
                subject=f"🔔 New {'Safari' if is_safari else 'Coastal'} Booking - {booking_data.get('park', booking_data.get('lodge', 'Booking'))} - {booking_id}",
                sender=sender_email,
                recipients=[admin_email],
                body=text_body,
                html=html_body
            )
            
            mail.send(msg)
            app.logger.info(f"✅ Admin notification sent to {admin_email} | Booking ID: {booking_id}")
            return booking_id
            
        except Exception as e:
            app.logger.error(f"❌ Failed to send admin email: {str(e)}")
            raise
    
    def send_confirmation_email(booking_data, booking_id):
        """Send confirmation email to customer"""
        try:
            customer_email = booking_data.get('email')
            if not customer_email:
                app.logger.warning("No customer email provided, skipping confirmation")
                return
            
            customer_name = booking_data.get('fullName', 'Valued Customer')
            first_name = customer_name.split()[0] if customer_name else 'Traveler'
            is_safari = booking_data.get('park') and 'National' in str(booking_data.get('park', ''))
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .greeting {{ font-size: 20px; color: #2c3e50; margin-bottom: 20px; }}
                    .message {{ color: #34495e; line-height: 1.6; margin-bottom: 20px; }}
                    .booking-details {{ background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 20px 0; }}
                    .detail-item {{ margin-bottom: 10px; }}
                    .detail-label {{ font-weight: bold; color: #495057; }}
                    .booking-id {{ background: #e8f5e9; padding: 15px; text-align: center; border-radius: 10px; margin: 20px 0; border: 2px solid #27ae60; }}
                    .booking-id-text {{ font-size: 18px; color: #155724; font-weight: bold; }}
                    .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef; text-align: center; color: #6c757d; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div style="font-size: 24px;">{'🦁' if is_safari else '🏖️'}</div>
                        <h1 style="margin: 10px 0 0 0;">Booking Confirmation</h1>
                    </div>
                    <div class="content">
                        <div class="greeting">
                            Dear {first_name}, 👋
                        </div>
                        
                        <div class="message">
                            Thank you for choosing <strong>Joztembo Tours</strong> for your {'safari adventure' if is_safari else 'coastal getaway'}! We're excited to help you plan an unforgettable experience in Kenya.
                        </div>
                        
                        <div class="booking-id">
                            <p style="margin: 0; font-size: 14px;">Your Booking Reference</p>
                            <div class="booking-id-text">{booking_id}</div>
                            <p style="margin: 10px 0 0 0; font-size: 12px; color: #6c757d;">Please save this for future reference</p>
                        </div>
                        
                        <div class="booking-details">
                            <h3 style="margin-top: 0; color: #2c3e50;">📋 Booking Summary</h3>
                            <div class="detail-item">
                                <span class="detail-label">Destination:</span> {booking_data.get('park', 'N/A')}
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Accommodation:</span> {booking_data.get('lodge', 'N/A')}
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Duration:</span> {booking_data.get('days', 'N/A')} days
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Guests:</span> {booking_data.get('travelers', 'N/A')} { 'person' if str(booking_data.get('travelers', '1')) == '1' else 'people' }
                            </div>
                        </div>
                        
                        <div class="message">
                            <strong>What happens next?</strong><br>
                            Our team will review your booking request and contact you within <strong>24 hours</strong> to confirm availability and provide you with a detailed quotation.
                        </div>
                        
                        <div class="message">
                            <strong>Need immediate assistance?</strong><br>
                            📞 Call: +254 722 609 492<br>
                            📧 Email: {app.config.get('MAIL_ADMIN_RECIPIENT', 'tembo4401@gmail.com')}
                        </div>
                        
                        <div class="footer">
                            <p>Best regards,</p>
                            <p><strong>The Joztembo Tours Team</strong></p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            =========================================
            JOZTEMBO TOURS - BOOKING CONFIRMATION
            =========================================
            
            Dear {first_name},
            
            Thank you for choosing Joztembo Tours!
            
            Your Booking Reference: {booking_id}
            
            BOOKING SUMMARY:
            - Destination: {booking_data.get('park', 'N/A')}
            - Accommodation: {booking_data.get('lodge', 'N/A')}
            - Duration: {booking_data.get('days', 'N/A')} days
            - Guests: {booking_data.get('travelers', 'N/A')}
            
            Our team will contact you within 24 hours.
            
            Contact: {app.config.get('MAIL_ADMIN_RECIPIENT', 'tembo4401@gmail.com')}
            Phone: +254 722 609 492
            
            Best regards,
            The Joztembo Tours Team
            =========================================
            """
            
            sender_email = app.config.get('MAIL_DEFAULT_SENDER') or app.config.get('MAIL_USERNAME')
            
            msg = Message(
                subject=f"✅ Booking Confirmed - {booking_data.get('park', booking_data.get('lodge', 'Your Booking'))} - {booking_id}",
                sender=sender_email,
                recipients=[customer_email],
                body=text_body,
                html=html_body
            )
            
            mail.send(msg)
            app.logger.info(f"✅ Confirmation email sent to {customer_email}")
            
        except Exception as e:
            app.logger.error(f"❌ Failed to send confirmation email: {str(e)}")
    
    # ============ CONTACT FORM EMAIL HELPERS ============
    
    def send_contact_admin_email(data, contact_id, emoji):
        """Send contact form notification to admin"""
        try:
            admin_email = app.config.get('MAIL_ADMIN_RECIPIENT')
            if not admin_email:
                raise ValueError("Admin recipient email not configured")
            
            sender_email = app.config.get('MAIL_DEFAULT_SENDER') or app.config.get('MAIL_USERNAME')
            
            subject_text = data.get('subject', 'General Inquiry')
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .field {{ margin-bottom: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px; border-left: 3px solid #f59e0b; }}
                    .label {{ font-weight: bold; color: #495057; display: block; margin-bottom: 5px; font-size: 14px; }}
                    .value {{ color: #212529; font-size: 16px; }}
                    .contact-id {{ background: #fff7ed; padding: 15px; text-align: center; border-radius: 8px; margin-bottom: 20px; border: 2px dashed #fbbf24; }}
                    .message-box {{ background: #fff7ed; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b; margin-top: 10px; }}
                    .timestamp {{ color: #6b7280; font-size: 12px; text-align: center; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin: 0;">{emoji} New Contact Form Submission</h1>
                        <p style="margin: 10px 0 0 0; opacity: 0.9;">From Joztembo Tours Website</p>
                    </div>
                    <div class="content">
                        <div class="contact-id">
                            <strong>Reference: <span style="color: #d97706;">{contact_id}</span></strong>
                        </div>
                        
                        <div class="field">
                            <span class="label">Subject</span>
                            <span class="value">{emoji} {subject_text}</span>
                        </div>
                        
                        <div class="field">
                            <span class="label">Full Name</span>
                            <span class="value">{data.get('fullName', 'N/A')}</span>
                        </div>
                        
                        <div class="field">
                            <span class="label">Email Address</span>
                            <span class="value"><a href="mailto:{data.get('email', '')}">{data.get('email', 'N/A')}</a></span>
                        </div>
                        
                        <div class="field">
                            <span class="label">Phone Number</span>
                            <span class="value">{data.get('phone', 'Not provided')}</span>
                        </div>
                        
                        <div class="field">
                            <span class="label">Message</span>
                            <div class="message-box">
                                {data.get('message', 'No message').replace(chr(10), '<br>')}
                            </div>
                        </div>
                        
                        <div class="timestamp">
                            Received: {datetime.now(UTC).strftime('%B %d, %Y at %I:%M %p UTC')}
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            =========================================
            JOZTEMBO TOURS - NEW CONTACT MESSAGE
            =========================================
            
            Reference: {contact_id}
            Subject: {emoji} {subject_text}
            
            FROM:
            Name: {data.get('fullName', 'N/A')}
            Email: {data.get('email', 'N/A')}
            Phone: {data.get('phone', 'Not provided')}
            
            MESSAGE:
            {data.get('message', 'No message')}
            
            Received: {datetime.now(UTC).strftime('%B %d, %Y at %I:%M %p UTC')}
            =========================================
            """
            
            msg = Message(
                subject=f"{emoji} Contact Form: {subject_text} - {contact_id}",
                sender=sender_email,
                recipients=[admin_email],
                body=text_body,
                html=html_body,
                reply_to=data.get('email')
            )
            
            mail.send(msg)
            app.logger.info(f"✅ Contact admin notification sent to {admin_email} | ID: {contact_id}")
            
        except Exception as e:
            app.logger.error(f"❌ Failed to send contact admin email: {str(e)}")
            raise
    
    def send_contact_confirmation(data, contact_id, emoji):
        """Send confirmation email to contact form submitter"""
        try:
            customer_email = data.get('email')
            if not customer_email:
                return
            
            customer_name = data.get('fullName', 'Valued Customer')
            first_name = customer_name.split()[0] if customer_name else 'Traveler'
            
            sender_email = app.config.get('MAIL_DEFAULT_SENDER') or app.config.get('MAIL_USERNAME')
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .greeting {{ font-size: 20px; color: #2c3e50; margin-bottom: 20px; }}
                    .message {{ color: #34495e; line-height: 1.6; margin-bottom: 20px; }}
                    .reference-box {{ background: #fff7ed; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; border: 2px solid #fbbf24; }}
                    .social-links {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #e9ecef; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div style="font-size: 24px;">{emoji}</div>
                        <h1 style="margin: 10px 0 0 0;">Message Received!</h1>
                    </div>
                    <div class="content">
                        <div class="greeting">
                            Dear {first_name}, 👋
                        </div>
                        
                        <div class="message">
                            Thank you for reaching out to <strong>Joztembo Tours</strong>! We've received your message and our team is excited to assist you.
                        </div>
                        
                        <div class="reference-box">
                            <p style="margin: 0; font-size: 14px; color: #92400e;">Your Reference Number</p>
                            <div style="font-size: 20px; color: #d97706; font-weight: bold; margin-top: 5px;">{contact_id}</div>
                            <p style="margin: 10px 0 0 0; font-size: 12px; color: #a16207;">Please save this for future reference</p>
                        </div>
                        
                        <div class="message">
                            <strong>What happens next?</strong><br>
                            • Our team will review your message<br>
                            • We typically respond within <strong>24 hours</strong><br>
                            • For urgent matters, call us directly at +254 722 609 492
                        </div>
                        
                        <div class="social-links">
                            <p style="font-weight: bold; color: #2c3e50;">Stay Connected:</p>
                            <p style="color: #34495e;">
                                📸 Instagram: @joztembotours<br>
                                📞 Phone: +254 722 609 492<br>
                                📧 Email: {app.config.get('MAIL_ADMIN_RECIPIENT', 'tembo4401@gmail.com')}
                            </p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg = Message(
                subject=f"✅ Message Received - Joztembo Tours ({contact_id})",
                sender=sender_email,
                recipients=[customer_email],
                html=html_body
            )
            
            mail.send(msg)
            app.logger.info(f"✅ Contact confirmation sent to {customer_email}")
            
        except Exception as e:
            app.logger.error(f"❌ Failed to send contact confirmation: {str(e)}")
    
    # ============ AUTH ROUTES ============
    
    @app.route("/api/auth/register", methods=["POST"])
    def register():
        """Register a new user"""
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data.get('name') or not data.get('email') or not data.get('password'):
                return jsonify({'success': False, 'error': 'Name, email, and password are required'}), 400
            
            # Validate email format
            email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
            if not email_pattern.match(data['email']):
                return jsonify({'success': False, 'error': 'Invalid email format'}), 400
            
            # Validate password length
            if len(data['password']) < 6:
                return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
            
            email = data['email'].lower().strip()
            
            # Check if email already exists
            if User.query.filter_by(email=email).first():
                return jsonify({'success': False, 'error': 'Email already registered'}), 400
            
            # Generate unique username from email
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                name=data['name'].strip(),
                email=email,
                username=username,
                phone=data.get('phone', '').strip()
            )
            user.set_password(data['password'])
            
            db.session.add(user)
            db.session.commit()
            
            token = user.generate_auth_token()
            
            app.logger.info(f"New user registered: {user.email} (username: {user.username})")
            
            return jsonify({
                'success': True,
                'token': token,
                'user': user.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Registration error: {str(e)}")
            return jsonify({'success': False, 'error': 'Registration failed. Please try again.'}), 500
    
    @app.route("/api/auth/login", methods=["POST"])
    def login():
        """Login user"""
        try:
            data = request.get_json()
            
            if not data.get('email') or not data.get('password'):
                return jsonify({'success': False, 'error': 'Email and password are required'}), 400
            
            login_id = data['email'].lower().strip()
            
            # Try to find user by email OR username
            user = User.query.filter(
                db.or_(User.email == login_id, User.username == login_id)
            ).first()
            
            if not user:
                return jsonify({'success': False, 'error': 'Invalid email/username or password'}), 401
            
            if not user.is_active:
                return jsonify({'success': False, 'error': 'Account has been deactivated. Please contact support.'}), 403
            
            if not user.check_password(data['password']):
                return jsonify({'success': False, 'error': 'Invalid email/username or password'}), 401
            
            token = user.generate_auth_token()
            
            app.logger.info(f"User logged in: {user.email}")
            
            return jsonify({
                'success': True,
                'token': token,
                'user': user.to_dict()
            }), 200
            
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            return jsonify({'success': False, 'error': 'Login failed. Please try again.'}), 500
    
    @app.route("/api/auth/me", methods=["GET"])
    @login_required
    def get_current_user():
        """Get current user info"""
        return jsonify({
            'success': True,
            'user': g.current_user.to_dict()
        }), 200
    
    # ============ USER CRUD ROUTES ============
    
    @app.route("/api/users/profile", methods=["GET"])
    @login_required
    def get_profile():
        """Get current user's profile"""
        try:
            return jsonify({
                'success': True,
                'user': g.current_user.to_dict()
            }), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route("/api/users/profile", methods=["PUT"])
    @login_required
    def update_profile():
        """Update current user's profile"""
        try:
            data = request.get_json()
            user = g.current_user
            
            changes = []
            
            if 'name' in data and data['name'].strip() != user.name:
                changes.append(f"name updated")
                user.name = data['name'].strip()
            
            if 'phone' in data:
                new_phone = data['phone'].strip()
                if new_phone != user.phone:
                    changes.append(f"phone updated")
                    user.phone = new_phone
            
            if 'email' in data:
                new_email = data['email'].lower().strip()
                if new_email != user.email:
                    existing = User.query.filter_by(email=new_email).first()
                    if existing and existing.id != user.id:
                        return jsonify({'success': False, 'error': 'Email already in use by another account'}), 400
                    changes.append(f"email updated")
                    user.email = new_email
            
            if changes:
                user.updated_at = datetime.now(UTC)
                db.session.commit()
                app.logger.info(f"Profile updated for user {user.id}")
            
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully',
                'user': user.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Profile update error: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to update profile'}), 500
    
    @app.route("/api/users/change-password", methods=["PUT"])
    @login_required
    def change_password():
        """Change current user's password"""
        try:
            data = request.get_json()
            user = g.current_user
            
            if not data.get('current_password'):
                return jsonify({'success': False, 'error': 'Current password is required'}), 400
            
            if not user.check_password(data['current_password']):
                return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400
            
            new_password = data.get('new_password', '')
            if not new_password or len(new_password) < 6:
                return jsonify({'success': False, 'error': 'New password must be at least 6 characters'}), 400
            
            user.set_password(new_password)
            user.updated_at = datetime.now(UTC)
            db.session.commit()
            
            app.logger.info(f"Password changed for user {user.id}")
            
            return jsonify({
                'success': True,
                'message': 'Password changed successfully'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Password change error: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to change password'}), 500
    
    @app.route("/api/users/account", methods=["DELETE"])
    @login_required
    def delete_account():
        """Delete current user's account"""
        try:
            data = request.get_json()
            user = g.current_user
            
            if not data.get('password'):
                return jsonify({'success': False, 'error': 'Password is required to delete account'}), 400
            
            if not user.check_password(data['password']):
                return jsonify({'success': False, 'error': 'Incorrect password'}), 400
            
            user.is_active = False
            user.updated_at = datetime.now(UTC)
            db.session.commit()
            
            app.logger.info(f"Account deleted for user {user.id} ({user.email})")
            
            return jsonify({
                'success': True,
                'message': 'Account deleted successfully'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Account deletion error: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to delete account'}), 500
    
    # ============ ADMIN USER MANAGEMENT ROUTES ============
    
    @app.route("/api/admin/users", methods=["GET"])
    @admin_required
    def get_all_users():
        """Get all users (admin only)"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            search = request.args.get('search', '', type=str)
            
            query = User.query
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    db.or_(
                        User.name.ilike(search_term),
                        User.email.ilike(search_term),
                        User.username.ilike(search_term),
                        User.phone.ilike(search_term)
                    )
                )
            
            query = query.order_by(User.created_at.desc())
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            users = pagination.items
            
            return jsonify({
                'success': True,
                'data': [user.to_dict() for user in users],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error fetching users: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route("/api/admin/users/<int:user_id>", methods=["GET"])
    @admin_required
    def get_user(user_id):
        """Get a specific user (admin only)"""
        try:
            user = User.query.get(user_id)
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            return jsonify({
                'success': True,
                'data': user.to_dict()
            }), 200
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route("/api/admin/users/<int:user_id>", methods=["PUT"])
    @admin_required
    def admin_update_user(user_id):
        """Update any user (admin only)"""
        try:
            user = User.query.get(user_id)
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            data = request.get_json()
            
            if 'name' in data and data['name'].strip():
                user.name = data['name'].strip()
            
            if 'email' in data and data['email'].strip():
                new_email = data['email'].lower().strip()
                if new_email != user.email:
                    existing = User.query.filter_by(email=new_email).first()
                    if existing and existing.id != user.id:
                        return jsonify({'success': False, 'error': 'Email already in use'}), 400
                    user.email = new_email
            
            if 'phone' in data:
                user.phone = data['phone'].strip()
            
            if 'is_admin' in data:
                user.is_admin = data['is_admin']
            
            if 'is_deputy' in data:
                user.is_deputy = data['is_deputy']
            
            if 'is_active' in data:
                user.is_active = data['is_active']
            
            user.updated_at = datetime.now(UTC)
            db.session.commit()
            
            app.logger.info(f"Admin {g.current_user.id} updated user {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'User updated successfully',
                'data': user.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Admin update error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
    @admin_required
    def admin_delete_user(user_id):
        """Delete/deactivate any user (admin only)"""
        try:
            user = User.query.get(user_id)
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            if user.id == g.current_user.id:
                return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
            
            user.is_active = False
            user.updated_at = datetime.now(UTC)
            db.session.commit()
            
            app.logger.info(f"Admin {g.current_user.id} deactivated user {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'User deactivated successfully'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Admin delete error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route("/api/admin/users/<int:user_id>/reactivate", methods=["POST"])
    @admin_required
    def admin_reactivate_user(user_id):
        """Reactivate a deactivated user (admin only)"""
        try:
            user = User.query.get(user_id)
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            if user.is_active:
                return jsonify({'success': False, 'error': 'User is already active'}), 400
            
            user.is_active = True
            user.updated_at = datetime.now(UTC)
            db.session.commit()
            
            app.logger.info(f"Admin {g.current_user.id} reactivated user {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'User reactivated successfully',
                'data': user.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Reactivate error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ============ REVIEW ROUTES ============
    
    @app.route("/api/reviews", methods=["GET"])
    def get_reviews():
        """Get all active reviews with optional filtering"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            sort_by = request.args.get('sort_by', 'created_at')
            order = request.args.get('order', 'desc')
            
            query = CustomerReview.query.filter_by(is_active=True)
            
            if sort_by == 'rating':
                query = query.order_by(CustomerReview.rating.desc() if order == 'desc' else CustomerReview.rating.asc())
            else:
                query = query.order_by(CustomerReview.created_at.desc() if order == 'desc' else CustomerReview.created_at.asc())
            
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            reviews = pagination.items
            
            avg_rating = db.session.query(db.func.avg(CustomerReview.rating))\
                .filter(CustomerReview.is_active == True).scalar()
            
            return jsonify({
                'success': True,
                'data': [review.to_dict() for review in reviews],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                },
                'stats': {
                    'total_reviews': pagination.total,
                    'average_rating': round(float(avg_rating), 1) if avg_rating else 0
                }
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error fetching reviews: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # Anyone can post a review (auth optional, supports reviewer_name)
    @app.route("/api/reviews", methods=["POST"])
    @optional_auth
    def create_review():
        """Create a new review - anyone can post, auth is optional"""
        try:
            data = request.get_json()
            
            rating = data.get('rating', 0)
            if not 1 <= rating <= 5:
                return jsonify({'success': False, 'error': 'Rating must be between 1 and 5'}), 400
            
            if not data.get('title') or not data.get('content'):
                return jsonify({'success': False, 'error': 'Title and content are required'}), 400
            
            user_id = None
            reviewer_name = None
            
            if g.current_user:
                user_id = g.current_user.id
            else:
                reviewer_name = data.get('reviewer_name', '').strip()
                if not reviewer_name:
                    reviewer_name = 'Anonymous'
            
            visit_date = None
            if data.get('visit_date'):
                try:
                    visit_date = datetime.strptime(data['visit_date'], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'success': False, 'error': 'Invalid visit date format. Use YYYY-MM-DD'}), 400
            
            review = CustomerReview(
                user_id=user_id,
                reviewer_name=reviewer_name,
                rating=rating,
                title=data['title'].strip(),
                content=data['content'].strip(),
                visit_date=visit_date,
                package_used=data.get('package_used', '').strip()
            )
            
            db.session.add(review)
            db.session.commit()
            
            display_name = g.current_user.name if g.current_user else reviewer_name
            app.logger.info(f"Review created by {display_name}")
            
            return jsonify({
                'success': True,
                'message': 'Review submitted successfully',
                'data': review.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating review: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # ✅ UPDATED: ANY signed-in user can edit ANY review (no ownership check)
    @app.route("/api/reviews/<int:review_id>", methods=["PUT"])
    @login_required
    def update_review(review_id):
        """Update a review - any authenticated user can update any review"""
        try:
            review = CustomerReview.query.get(review_id)
            
            if not review or not review.is_active:
                return jsonify({'success': False, 'error': 'Review not found'}), 404
            
            # ✅ REMOVED ownership check - any authenticated user can edit any review
            
            data = request.get_json()
            
            if 'rating' in data:
                if not 1 <= data['rating'] <= 5:
                    return jsonify({'success': False, 'error': 'Rating must be between 1 and 5'}), 400
                review.rating = data['rating']
            
            if 'title' in data:
                review.title = data['title'].strip()
            
            if 'content' in data:
                review.content = data['content'].strip()
            
            if 'visit_date' in data:
                if data['visit_date']:
                    try:
                        review.visit_date = datetime.strptime(data['visit_date'], '%Y-%m-%d').date()
                    except ValueError:
                        return jsonify({'success': False, 'error': 'Invalid visit date format'}), 400
                else:
                    review.visit_date = None
            
            if 'package_used' in data:
                review.package_used = data['package_used'].strip()
            
            if 'reviewer_name' in data and g.current_user.is_admin:
                review.reviewer_name = data['reviewer_name'].strip() if data['reviewer_name'] else None
            
            review.is_edited = True
            review.edited_at = datetime.now(UTC)
            review.updated_at = datetime.now(UTC)
            
            db.session.commit()
            
            app.logger.info(f"Review {review_id} updated by user {g.current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'Review updated successfully',
                'data': review.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating review: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ✅ UPDATED: ANY signed-in user can delete ANY review (no ownership check)
    @app.route("/api/reviews/<int:review_id>", methods=["DELETE"])
    @login_required
    def delete_review(review_id):
        """Delete a review - any authenticated user can delete any review"""
        try:
            review = CustomerReview.query.get(review_id)
            
            if not review:
                return jsonify({'success': False, 'error': 'Review not found'}), 404
            
            # ✅ REMOVED ownership check - any authenticated user can delete any review
            
            review.is_active = False
            review.updated_at = datetime.now(UTC)
            db.session.commit()
            
            app.logger.info(f"Review {review_id} deleted by user {g.current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'Review deleted successfully'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting review: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ============ REVIEW REPLY ROUTES ============
    
    @app.route("/api/reviews/<int:review_id>/replies", methods=["GET"])
    def get_review_replies(review_id):
        """Get replies for a review"""
        try:
            replies = ReviewReply.query.filter_by(review_id=review_id, is_active=True)\
                .order_by(ReviewReply.created_at.asc()).all()
            
            return jsonify({
                'success': True,
                'data': [reply.to_dict() for reply in replies]
            }), 200
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Any authenticated user can reply to reviews
    @app.route("/api/reviews/<int:review_id>/replies", methods=["POST"])
    @login_required
    def create_reply(review_id):
        """Create a reply to a review (any authenticated user can reply)"""
        try:
            review = CustomerReview.query.get(review_id)
            
            if not review:
                return jsonify({'success': False, 'error': 'Review not found'}), 404
            
            data = request.get_json()
            
            if not data.get('content'):
                return jsonify({'success': False, 'error': 'Reply content is required'}), 400
            
            reply = ReviewReply(
                review_id=review_id,
                user_id=g.current_user.id,
                content=data['content']
            )
            
            db.session.add(reply)
            db.session.commit()
            
            app.logger.info(f"Reply created for review {review_id} by user {g.current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'Reply added successfully',
                'data': reply.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating reply: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Users can edit their own replies, admins can edit any
    @app.route("/api/replies/<int:reply_id>", methods=["PUT"])
    @login_required
    def update_reply(reply_id):
        """Update a reply - owner or admin only"""
        try:
            reply = ReviewReply.query.get(reply_id)
            
            if not reply or not reply.is_active:
                return jsonify({'success': False, 'error': 'Reply not found'}), 404
            
            # Check permission: user owns the reply OR is admin
            if not g.current_user.is_admin and reply.user_id != g.current_user.id:
                return jsonify({'success': False, 'error': 'You can only edit your own replies'}), 403
            
            data = request.get_json()
            
            if not data.get('content'):
                return jsonify({'success': False, 'error': 'Content is required'}), 400
            
            reply.content = data['content']
            reply.is_edited = True
            reply.edited_at = datetime.now(UTC)
            
            db.session.commit()
            
            app.logger.info(f"Reply {reply_id} updated by user {g.current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'Reply updated successfully',
                'data': reply.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating reply: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Users can delete their own replies, admins can delete any
    @app.route("/api/replies/<int:reply_id>", methods=["DELETE"])
    @login_required
    def delete_reply(reply_id):
        """Delete a reply - owner or admin only"""
        try:
            reply = ReviewReply.query.get(reply_id)
            
            if not reply:
                return jsonify({'success': False, 'error': 'Reply not found'}), 404
            
            # Check permission: user owns the reply OR is admin
            if not g.current_user.is_admin and reply.user_id != g.current_user.id:
                return jsonify({'success': False, 'error': 'You can only delete your own replies'}), 403
            
            reply.is_active = False
            db.session.commit()
            
            app.logger.info(f"Reply {reply_id} deleted by user {g.current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'Reply deleted successfully'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting reply: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ============ REVIEW STATS ============
    
    @app.route("/api/reviews/stats", methods=["GET"])
    def get_review_stats():
        """Get review statistics"""
        try:
            total_reviews = CustomerReview.query.filter_by(is_active=True).count()
            avg_rating = db.session.query(db.func.avg(CustomerReview.rating))\
                .filter(CustomerReview.is_active == True).scalar()
            
            rating_distribution = {}
            for i in range(1, 6):
                count = CustomerReview.query.filter_by(rating=i, is_active=True).count()
                rating_distribution[str(i)] = count
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_reviews': total_reviews,
                    'average_rating': round(float(avg_rating), 1) if avg_rating else 0,
                    'rating_distribution': rating_distribution
                }
            }), 200
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ============ SAFARI PACKAGE CRUD ROUTES ============
    
    @app.route("/api/safari-cards", methods=["POST"])
    def create_safari_package():
        """Create a new safari package with full details"""
        try:
            data = request.get_json()
            
            if not data.get('name'):
                return jsonify({"success": False, "error": "Package name is required"}), 400
            
            package = SafariPackage(
                name=data['name'],
                description=data.get('description', ''),
                total_days=data.get('total_days', 5),
                total_nights=data.get('total_nights', 4),
                is_active=data.get('is_active', True)
            )
            db.session.add(package)
            db.session.flush()
            
            if data.get('days'):
                for day_data in data['days']:
                    package_day = PackageDay(
                        package_id=package.id,
                        day_number=day_data['day_number'],
                        title=day_data.get('title', f"Day {day_data['day_number']}"),
                        description=day_data.get('description', ''),
                        activities=day_data.get('activities', []),
                        meals=day_data.get('meals', []),
                        park_name=day_data.get('park_name', ''),
                        park_description=day_data.get('park_description', '')
                    )
                    db.session.add(package_day)
            
            if data.get('priceOptions'):
                default_itinerary = PackageItinerary(
                    package_id=package.id,
                    itinerary_code=f"DEFAULT-{package.id}",
                    name="Default Itinerary",
                    is_default=True
                )
                db.session.add(default_itinerary)
                db.session.flush()
                
                for price_option in data['priceOptions']:
                    people = price_option.get('people', 2)
                    price_value = price_option.get('price', 0)
                    
                    package_price = PackagePrice(
                        package_id=package.id,
                        itinerary_id=default_itinerary.id,
                        pax_2_price=price_value if people == 2 else 0,
                        pax_4_price=price_value if people == 4 else 0,
                        pax_6_price=price_value if people == 6 else 0,
                        pax_8_price=price_value if people == 8 else 0,
                        valid_from=datetime.now().date(),
                        valid_to=datetime.now().date().replace(year=datetime.now().year + 1),
                        includes=data.get('includes', []),
                        excludes=data.get('excludes', [])
                    )
                    db.session.add(package_price)
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Safari package created successfully",
                "package_id": package.id,
                "data": package.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating safari package: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/safari-cards", methods=["GET"])
    def get_all_safari_packages():
        """Get all safari packages"""
        try:
            packages = SafariPackage.query.filter_by(is_active=True).all()
            return jsonify({
                "success": True,
                "count": len(packages),
                "data": [pkg.to_dict() for pkg in packages]
            }), 200
        except Exception as e:
            app.logger.error(f"Error fetching safari packages: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/safari-cards/<int:package_id>", methods=["GET"])
    def get_safari_package(package_id):
        """Get a specific safari package by ID"""
        try:
            package = SafariPackage.query.get(package_id)
            if not package:
                return jsonify({"success": False, "error": "Package not found"}), 404
            return jsonify({
                "success": True,
                "data": package.to_dict()
            }), 200
        except Exception as e:
            app.logger.error(f"Error fetching safari package: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/safari-cards/<int:package_id>", methods=["PUT"])
    def update_safari_package(package_id):
        """Update an existing safari package"""
        try:
            package = SafariPackage.query.get(package_id)
            if not package:
                return jsonify({"success": False, "error": "Package not found"}), 404
            
            data = request.get_json()
            
            if 'name' in data:
                package.name = data['name']
            if 'description' in data:
                package.description = data['description']
            if 'total_days' in data:
                package.total_days = data['total_days']
                package.total_nights = data['total_days'] - 1
            if 'is_active' in data:
                package.is_active = data['is_active']
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Safari package updated successfully",
                "data": package.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating safari package: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/safari-cards/<int:package_id>", methods=["DELETE"])
    def delete_safari_package(package_id):
        """Soft delete a safari package"""
        try:
            package = SafariPackage.query.get(package_id)
            if not package:
                return jsonify({"success": False, "error": "Package not found"}), 404
            
            package.is_active = False
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Safari package deleted successfully"
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting safari package: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/safari-cards/<int:package_id>/permanent", methods=["DELETE"])
    def permanent_delete_safari_package(package_id):
        """Permanently delete a safari package and all related data"""
        try:
            package = SafariPackage.query.get(package_id)
            if not package:
                return jsonify({"success": False, "error": "Package not found"}), 404
            
            db.session.delete(package)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Safari package permanently deleted"
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error permanently deleting safari package: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    # ============ PARK CRUD ROUTES ============
    
    @app.route("/api/parks", methods=["GET"])
    def get_all_parks():
        """Get all parks"""
        try:
            parks = Park.query.filter_by(is_active=True).all()
            return jsonify({
                "success": True,
                "data": [park.to_dict() for park in parks]
            }), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/parks", methods=["POST"])
    def create_park():
        """Create a new park"""
        try:
            data = request.get_json()
            
            park = Park(
                name=data['name'],
                location=data.get('location', ''),
                description=data.get('description', ''),
                known_for=data.get('known_for', [])
            )
            db.session.add(park)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "data": park.to_dict()
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
    
    # ============ BOOKING ROUTE ============
    
    @app.route("/api/send-booking", methods=["POST", "OPTIONS"])
    def send_booking():
        """Handle booking request and send email notifications"""
        if request.method == "OPTIONS":
            return jsonify({"success": True}), 200
        
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"success": False, "error": "No data provided"}), 400
            
            required_fields = ['fullName', 'email', 'phone', 'park', 'lodge', 'travelers']
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                return jsonify({
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }), 400
            
            booking_id = send_admin_email(data)
            
            try:
                send_confirmation_email(data, booking_id)
            except Exception as e:
                app.logger.warning(f"Customer confirmation email failed (non-critical): {e}")
            
            return jsonify({
                "success": True,
                "bookingId": booking_id,
                "message": "Booking request received successfully! We'll contact you within 24 hours."
            }), 200
            
        except Exception as e:
            app.logger.error(f"Booking error: {str(e)}")
            return jsonify({
                "success": False,
                "error": "Failed to process booking. Please try again or contact us directly."
            }), 500
    
    # ============ CONTACT FORM ROUTE ============
    
    @app.route("/api/send-contact", methods=["POST", "OPTIONS"])
    def send_contact():
        """Handle contact form submissions and send email notifications"""
        if request.method == "OPTIONS":
            return jsonify({"success": True}), 200
        
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"success": False, "error": "No data provided"}), 400
            
            required_fields = ['fullName', 'email', 'subject', 'message']
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                return jsonify({
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }), 400
            
            contact_id = f"CONTACT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
            
            subject_emoji_map = {
                "Safari Booking": "🏕️",
                "Beach Tour": "🏖️",
                "Custom Package": "🎯",
                "Airport Transfer": "🚗",
                "General Inquiry": "💬",
                "Partnership": "🤝",
                "Feedback": "📝",
                "Other": "📌"
            }
            
            emoji = subject_emoji_map.get(data.get('subject', 'General Inquiry'), '💬')
            
            send_contact_admin_email(data, contact_id, emoji)
            
            try:
                send_contact_confirmation(data, contact_id, emoji)
            except Exception as e:
                app.logger.warning(f"Contact confirmation email failed (non-critical): {e}")
            
            app.logger.info(f"Contact form submitted: {contact_id} from {data.get('email')}")
            
            return jsonify({
                "success": True,
                "contactId": contact_id,
                "message": "Thank you for your message! We'll get back to you within 24 hours."
            }), 200
            
        except Exception as e:
            app.logger.error(f"Contact form error: {str(e)}")
            return jsonify({
                "success": False,
                "error": "Failed to send message. Please try again or contact us directly at +254 722 609 492."
            }), 500
    
    @app.route("/api/test-email", methods=["GET"])
    def test_email():
        """Test email configuration"""
        try:
            admin_email = app.config.get('MAIL_ADMIN_RECIPIENT')
            if not admin_email:
                return jsonify({
                    "success": False,
                    "error": "Admin recipient email not configured"
                }), 500
            
            sender_email = app.config.get('MAIL_DEFAULT_SENDER') or app.config.get('MAIL_USERNAME')
            
            msg = Message(
                subject="✅ TEST EMAIL - Safari Booking System",
                sender=sender_email,
                recipients=[admin_email],
                body=f"""
                This is a test email from your Safari Booking System.
                
                Configuration Test:
                - Timestamp: {datetime.now(UTC).isoformat()}
                - Environment: {os.environ.get('FLASK_ENV', 'development')}
                - Mail Server: {app.config['MAIL_SERVER']}
                
                If you received this, your email configuration is working! 🎉
                """
            )
            mail.send(msg)
            
            return jsonify({
                "success": True,
                "message": f"Test email sent to {admin_email}",
                "config": {
                    "mail_server": app.config['MAIL_SERVER'],
                    "mail_port": app.config['MAIL_PORT'],
                    "mail_username": app.config['MAIL_USERNAME'],
                    "environment": os.environ.get('FLASK_ENV', 'development')
                }
            }), 200
            
        except Exception as e:
            app.logger.error(f"Test email failed: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e),
                "config": {
                    "mail_server": app.config['MAIL_SERVER'],
                    "mail_port": app.config['MAIL_PORT'],
                    "mail_username": app.config['MAIL_USERNAME'],
                    "mail_use_tls": app.config['MAIL_USE_TLS'],
                }
            }), 500
    
    @app.route("/api/health", methods=["GET"])
    def health():
        """Health check endpoint"""
        email_configured = bool(app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'))
        db_connected = False
        try:
            db.session.execute(db.text('SELECT 1'))
            db_connected = True
        except Exception as e:
            app.logger.warning(f"Database connection check failed: {e}")
        
        return jsonify({
            "status": "healthy" if (email_configured and db_connected) else "degraded",
            "timestamp": datetime.now(UTC).isoformat(),
            "email_configured": email_configured,
            "database_connected": db_connected,
            "environment": os.environ.get('FLASK_ENV', 'development'),
            "debug": app.config.get('DEBUG', False)
        }), 200
    
    @app.route("/")
    def index():
        return jsonify({
            "message": "🦁 Joztembo Tours - Safari Booking System API",
            "version": "5.0",
            "documentation": "/api/health",
            "endpoints": {
                "auth": {
                    "POST /api/auth/register": "Register new user",
                    "POST /api/auth/login": "Login user",
                    "GET /api/auth/me": "Get current user (auth required)"
                },
                "user_crud": {
                    "GET /api/users/profile": "Get current user profile",
                    "PUT /api/users/profile": "Update profile (name, email, phone)",
                    "PUT /api/users/change-password": "Change password",
                    "DELETE /api/users/account": "Delete own account (requires password)"
                },
                "admin_users": {
                    "GET /api/admin/users": "Get all users (admin only, with pagination)",
                    "GET /api/admin/users/<id>": "Get specific user (admin only)",
                    "PUT /api/admin/users/<id>": "Update any user (admin only)",
                    "DELETE /api/admin/users/<id>": "Deactivate user (admin only)",
                    "POST /api/admin/users/<id>/reactivate": "Reactivate user (admin only)"
                },
                "reviews": {
                    "GET /api/reviews": "Get all reviews (with pagination)",
                    "POST /api/reviews": "✅ Create review (anyone - auth optional, supports reviewer_name)",
                    "PUT /api/reviews/<id>": "✅ UPDATE ANY REVIEW (any authenticated user)",
                    "DELETE /api/reviews/<id>": "✅ DELETE ANY REVIEW (any authenticated user)",
                    "GET /api/reviews/stats": "Get review statistics",
                    "GET /api/reviews/<id>/replies": "Get replies for a review",
                    "POST /api/reviews/<id>/replies": "✅ Create reply (any authenticated user)",
                    "PUT /api/replies/<id>": "✅ Update reply (owner or admin)",
                    "DELETE /api/replies/<id>": "✅ Delete reply (owner or admin)"
                },
                "booking": {
                    "POST /api/send-booking": "Submit a booking request",
                    "POST /api/send-contact": "Submit a contact form message"
                },
                "safari_packages": {
                    "GET /api/safari-cards": "Get all safari packages",
                    "GET /api/safari-cards/<id>": "Get single package",
                    "POST /api/safari-cards": "Create new package",
                    "PUT /api/safari-cards/<id>": "Update package",
                    "DELETE /api/safari-cards/<id>": "Soft delete package",
                    "DELETE /api/safari-cards/<id>/permanent": "Permanent delete"
                },
                "parks": {
                    "GET /api/parks": "Get all parks",
                    "POST /api/parks": "Create new park"
                },
                "utilities": {
                    "GET /api/test-email": "Test email configuration",
                    "GET /api/health": "System health check"
                }
            }
        }), 200

# ============ APP INITIALIZATION ============

# Create app instance
app = create_app()

if __name__ == "__main__":
    # This only runs when executing directly (not on Render with Gunicorn)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)