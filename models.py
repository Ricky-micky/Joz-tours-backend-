# models.py - KEEP YOUR ORIGINAL MODELS AND ADD NEW ONES
from datetime import datetime
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

# ORIGINAL MODELS (keep these)
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
    
    # NEW: Safari relationships
    safari_reviews = db.relationship('SafariReview', backref='author', lazy=True)
    safari_comments = db.relationship('SafariComment', backref='author', lazy=True)
    
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

# NEW SAFARI PACKAGE MODELS (add these at the bottom)
class SafariPackage(db.Model):
    __tablename__ = 'safari_packages'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    total_days = db.Column(db.Integer, nullable=False)
    total_nights = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    package_days = db.relationship('PackageDay', backref='package', lazy=True, order_by='PackageDay.day_number')
    itineraries = db.relationship('PackageItinerary', backref='package', lazy=True)
    prices = db.relationship('PackagePrice', backref='package', lazy=True)
    reviews = db.relationship('SafariReview', backref='package', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'total_days': self.total_days,
            'total_nights': self.total_nights,
            'review_count': len(self.reviews),
            'days': [day.to_dict() for day in self.package_days],
            'itineraries': [itinerary.to_dict() for itinerary in self.itineraries],
            'prices': [price.to_dict() for price in self.prices],
            'created_at': self.created_at.isoformat()
        }

class PackageDay(db.Model):
    __tablename__ = 'package_days'
    
    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey('safari_packages.id'), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    activities = db.Column(db.JSON)
    meals = db.Column(db.JSON)
    park_name = db.Column(db.String(100), nullable=False)
    park_description = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'day_number': self.day_number,
            'title': self.title,
            'description': self.description,
            'activities': self.activities or [],
            'meals': self.meals or [],
            'park_name': self.park_name,
            'park_description': self.park_description
        }

class PackageItinerary(db.Model):
    __tablename__ = 'package_itineraries'
    
    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey('safari_packages.id'), nullable=False)
    itinerary_code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=False)
    
    day_accommodations = db.relationship('ItineraryAccommodation', backref='itinerary', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'itinerary_code': self.itinerary_code,
            'name': self.name,
            'description': self.description,
            'is_default': self.is_default,
            'accommodations': [acc.to_dict() for acc in self.day_accommodations]
        }

class ItineraryAccommodation(db.Model):
    __tablename__ = 'itinerary_accommodations'
    
    id = db.Column(db.Integer, primary_key=True)
    itinerary_id = db.Column(db.Integer, db.ForeignKey('package_itineraries.id'), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    accommodation_name = db.Column(db.String(200), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'day_number': self.day_number,
            'accommodation_name': self.accommodation_name
        }

class PackagePrice(db.Model):
    __tablename__ = 'package_prices'
    
    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey('safari_packages.id'), nullable=False)
    itinerary_id = db.Column(db.Integer, db.ForeignKey('package_itineraries.id'), nullable=False)
    
    pax_2_price = db.Column(db.Float, nullable=False)
    pax_4_price = db.Column(db.Float, nullable=False)
    pax_6_price = db.Column(db.Float, nullable=False)
    pax_8_price = db.Column(db.Float, nullable=False)
    
    single_supplement = db.Column(db.Float)
    child_price = db.Column(db.Float)
    
    includes = db.Column(db.JSON)
    excludes = db.Column(db.JSON)
    
    valid_from = db.Column(db.Date, nullable=False)
    valid_to = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'package_id': self.package_id,
            'itinerary_id': self.itinerary_id,
            'prices': {
                'pax_2': self.pax_2_price,
                'pax_4': self.pax_4_price,
                'pax_6': self.pax_6_price,
                'pax_8': self.pax_8_price
            },
            'single_supplement': self.single_supplement,
            'child_price': self.child_price,
            'includes': self.includes or [],
            'excludes': self.excludes or [],
            'valid_from': self.valid_from.isoformat(),
            'valid_to': self.valid_to.isoformat(),
            'is_active': self.is_active
        }

class SafariReview(db.Model):
    __tablename__ = 'safari_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey('safari_packages.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('SafariComment', backref='review', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'package_id': self.package_id,
            'author': self.author.to_dict() if self.author else None,
            'message': self.message,
            'is_approved': self.is_approved,
            'comment_count': len(self.comments),
            'created_at': self.created_at.isoformat()
        }

class SafariComment(db.Model):
    __tablename__ = 'safari_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('safari_reviews.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'review_id': self.review_id,
            'author': self.author.to_dict() if self.author else None,
            'message': self.message,
            'is_approved': self.is_approved,
            'created_at': self.created_at.isoformat()
        }

class Park(db.Model):
    __tablename__ = 'parks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(200))
    description = db.Column(db.Text)
    known_for = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'description': self.description,
            'known_for': self.known_for or [],
            'is_active': self.is_active
        }