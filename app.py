from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from models import db, CustomerRemark
from flask_cors import CORS
import os

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow all origins since it's a public website

# Database configuration - Update with your Joz Tembo Tours database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://your_username:your_password@your_host/your_database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db with the app
db.init_app(app)

# Register blueprints
from remarks_bp import remarks_bp
app.register_blueprint(remarks_bp)

# Create database tables
with app.app_context():
    db.create_all()

# Simple home route
@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to Joz Tembo Tours API",
        "version": "1.0",
        "endpoints": {
            "submit_remark": "POST /remarks",
            "get_remarks": "GET /remarks",
            "get_stats": "GET /remarks/stats",
            "get_remark": "GET /remarks/<id>"
        }
    })

# Health check
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)