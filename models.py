from datetime import datetime
from extensions import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    is_admin = db.Column(db.Boolean, default=False)
    is_deputy = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    comments = db.relationship('Comment', backref='author', lazy=True)
    stories = db.relationship('Story', backref='author', lazy=True)
    reviews = db.relationship('Review', backref='author', lazy=True)
    price_histories = db.relationship('PriceHistory', backref='edited_by', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'is_admin': self.is_admin,
            'is_deputy': self.is_deputy,
            'created_at': self.created_at.isoformat()
        }
    
    def can_delete_comment(self, comment):
        """Check if user can delete a comment"""
        return self.is_admin or self.id == comment.user_id

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
  
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'author': self.author.to_dict() if self.author else None
        }

# Existing models below (simplified to remove image-related fields)
class Lodge(db.Model):
    __tablename__ = 'lodges'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    amenities = db.Column(db.JSON)  # List of amenities
    capacity = db.Column(db.Integer)
    rating = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    prices = db.relationship('LodgePrice', backref='lodge', lazy=True)
    reviews = db.relationship('Review', backref='lodge', lazy=True)

class LodgePrice(db.Model):
    __tablename__ = 'lodge_prices'
    
    id = db.Column(db.Integer, primary_key=True)
    lodge_id = db.Column(db.Integer, db.ForeignKey('lodges.id'), nullable=False)
    park_name = db.Column(db.String(100), nullable=False)
    number_of_days = db.Column(db.Integer, nullable=False)
    number_of_visitors = db.Column(db.Integer, nullable=False)
    price_per_person = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    season = db.Column(db.String(50))
    valid_from = db.Column(db.Date, nullable=False)
    valid_to = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class PriceHistory(db.Model):
    __tablename__ = 'price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    lodge_price_id = db.Column(db.Integer, db.ForeignKey('lodge_prices.id'), nullable=False)
    old_price = db.Column(db.Float, nullable=False)
    new_price = db.Column(db.Float, nullable=False)
    edited_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    change_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Story(db.Model):
    __tablename__ = 'stories'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lodge_id = db.Column(db.Integer, db.ForeignKey('lodges.id'))
    category = db.Column(db.String(50))
    tags = db.Column(db.JSON)  # List of tags
    is_featured = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    lodge_id = db.Column(db.Integer, db.ForeignKey('lodges.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    helpful_count = db.Column(db.Integer, default=0)
    verified_booking = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

class AdminActionLog(db.Model):
    __tablename__ = 'admin_action_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.Integer, nullable=False)
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    admin = db.relationship('User', backref='actions')