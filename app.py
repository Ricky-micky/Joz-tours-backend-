from flask import Flask, request, jsonify
from flask_mail import Mail, Message
from flask_cors import CORS, cross_origin
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # This enables CORS for all routes

# Flask configuration from environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///./safari_bookings.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail configuration from environment variables
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Initialize extensions
from extensions import db
db.init_app(app)

mail = Mail(app)

# Register Blueprints
from views.auth import auth_bp
from views.users import users_bp
from views.stories import stories_bp
from views.reviews import reviews_bp
from views.admin import admin_bp
from views.prices import prices_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(users_bp, url_prefix='/api/users')
app.register_blueprint(stories_bp, url_prefix='/api/stories')
app.register_blueprint(reviews_bp, url_prefix='/api/reviews')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(prices_bp, url_prefix='/api/prices')

@app.route('/api/send-booking', methods=['POST', 'OPTIONS'])
@cross_origin()
def send_booking():
    try:
        if request.method == 'OPTIONS':
            return jsonify({'message': 'CORS preflight successful'}), 200
        
        data = request.json
        
        # Required fields
        required_fields = ['park', 'lodge', 'days', 'travelers', 'totalPrice', 'fullName', 'email', 'phone']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Current time for booking ID
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Email to you
        msg_to_you = Message(
            subject=f"NEW SAFARI BOOKING: {data['park']}",
            sender=os.getenv('MAIL_DEFAULT_SENDER'),
            recipients=[os.getenv('MAIL_USERNAME')],
            body=f"""
            NEW SAFARI BOOKING REQUEST
            ============================
            
            TIMESTAMP: {current_time}
            
            PARK DETAILS:
            ------------
            Park: {data['park']}
            Highlights: {data.get('parkHighlights', 'N/A')}
            Best Time: {data.get('bestTime', 'N/A')}
            Wildlife: {data.get('wildlife', 'N/A')}
            Features: {data.get('specialFeature', 'N/A')}
            
            BOOKING DETAILS:
            ---------------
            Lodge: {data['lodge']}
            Description: {data.get('lodgeDescription', 'N/A')}
            Duration: {data['days']} days
            Travelers: {data['travelers']}
            Start Date: {data.get('startDate', 'Flexible')}
            Total Price: ${data['totalPrice']}
            
            ITINERARY:
            ---------
            {data.get('itinerary', 'N/A')}
            
            CUSTOMER INFO:
            -------------
            Name: {data['fullName']}
            Email: {data['email']}
            Phone: {data['phone']}
            
            MESSAGE:
            --------
            {data.get('message', 'No additional message')}
            
            ============================
            Booking ID: {current_time.replace(' ', '').replace(':', '').replace('-', '')}
            """
        )
        
        mail.send(msg_to_you)
        
        # Optional: Send confirmation email to customer
        confirmation_body = f"""
        Dear {data['fullName']},
        
        Thank you for your safari booking request with Joztembo Tours!
        
        We have received your booking request for:
        
        📍 Destination: {data['park']}
        🏨 Lodge: {data['lodge']}
        ⏱️ Duration: {data['days']} days
        👥 Travelers: {data['travelers']} people
        💰 Estimated Total: ${data['totalPrice']}
        
        Our team will review your request and contact you within 24 hours.
        
        Booking ID: {current_time.replace(' ', '').replace(':', '').replace('-', '')}
        
        Best regards,
        Joztembo Tours Team
        """
        
        if data['email'] != os.getenv('MAIL_USERNAME'):
            msg_to_customer = Message(
                subject=f"Booking Confirmation: {data['park']} Safari",
                sender=os.getenv('MAIL_DEFAULT_SENDER'),
                recipients=[data['email']],
                body=confirmation_body
            )
            mail.send(msg_to_customer)
        
        return jsonify({
            'success': True,
            'message': 'Booking request sent successfully! Check your email for confirmation.',
            'bookingId': current_time.replace(' ', '').replace(':', '').replace('-', '')
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
@cross_origin()
def health_check():
    return jsonify({'status': 'healthy', 'service': 'Safari Booking API'}), 200

@app.route('/')
def index():
    return jsonify({
        'message': 'Safari Booking API',
        'version': '1.0',
        'endpoints': {
            'health': '/api/health',
            'auth': '/api/auth/*',
            'users': '/api/users/*',
            'stories': '/api/stories/*',
            'reviews': '/api/reviews/*',
            'admin': '/api/admin/*',
            'prices': '/api/prices/*',
            'booking': '/api/send-booking'
        }
    })

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    print("🚀 Safari Booking Backend Starting...")
    print(f"📡 Server running at http://{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', 5000)}")
    print(f"🔗 Health Check: http://localhost:{os.getenv('PORT', 5000)}/api/health")
    print("\n📁 Registered Routes:")
    print("   • /api/auth/*      - Authentication routes")
    print("   • /api/users/*     - User management routes")
    print("   • /api/stories/*   - Stories routes")
    print("   • /api/reviews/*   - Reviews routes")
    print("   • /api/admin/*     - Admin routes")
    print("   • /api/prices/*    - Pricing routes")
    print("   • /api/send-booking - Booking email service")
    
    app.run(
        debug=os.getenv('DEBUG', 'False') == 'True',
        port=int(os.getenv('PORT', 5000)),
        host=os.getenv('HOST', '0.0.0.0')
    )