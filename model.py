from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class CustomerRemark(db.Model):
    __tablename__ = 'customer_remarks'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=True)
    tour_package = db.Column(db.String(200), nullable=False)
    remark = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    remark_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=True)  # Auto-approve since no admin panel
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'tour_package': self.tour_package,
            'remark': self.remark,
            'rating': self.rating,
            'remark_date': self.remark_date.isoformat()
        }

# Remove user relationship since no login required