from flask import Flask, request, jsonify
from flask_mail import Mail, Message
from flask_cors import CORS, cross_origin
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # This enables CORS for all routes

# Mail configuration for Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'tembo4401@gmail.com'
app.config['MAIL_PASSWORD'] = 'axyc zqwt svai xgnq'  # Your app password
app.config['MAIL_DEFAULT_SENDER'] = 'tembo4401@gmail.com'

mail = Mail(app)

@app.route('/api/send-booking', methods=['POST', 'OPTIONS'])
@cross_origin()  # Now this will work
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
            sender='tembo4401@gmail.com',
            recipients=['tembo4401@gmail.com'],
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
        
        if data['email'] != 'tembo4401@gmail.com':
            msg_to_customer = Message(
                subject=f"Booking Confirmation: {data['park']} Safari",
                sender='tembo4401@gmail.com',
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

if __name__ == '__main__':
    print("🚀 Safari Booking Backend Starting...")
    print("📡 Server running at http://localhost:5000")
    print("🔗 Health Check: http://localhost:5000/api/health")
    app.run(debug=True, port=5000, host='0.0.0.0')