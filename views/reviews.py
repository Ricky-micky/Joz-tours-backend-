# routes/reviews.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Review, SafariReview, Lodge, SafariPackage, User
from datetime import datetime

reviews_bp = Blueprint('reviews', __name__)

# Helper function to add to_dict method to Review model
def review_to_dict(review):
    """Convert Review object to dictionary"""
    return {
        'id': review.id,
        'lodge_id': review.lodge_id,
        'author': review.author.to_dict() if review.author else None,
        'rating': review.rating,
        'title': review.title,
        'content': review.content,
        'helpful_count': review.helpful_count,
        'verified_booking': review.verified_booking,
        'is_approved': review.is_approved,
        'created_at': review.created_at.isoformat(),
        'updated_at': review.updated_at.isoformat() if review.updated_at else None
    }

# =============================================
# LODGE REVIEWS ROUTES
# =============================================

@reviews_bp.route('/lodges/<int:lodge_id>/reviews', methods=['GET'])
def get_lodge_reviews(lodge_id):
    """Get all reviews for a specific lodge"""
    reviews = Review.query.filter_by(lodge_id=lodge_id, is_approved=True).all()
    return jsonify({
        'reviews': [review_to_dict(review) for review in reviews]
    }), 200

@reviews_bp.route('/lodges/<int:lodge_id>/reviews', methods=['POST'])
@jwt_required()
def create_lodge_review(lodge_id):
    """Create a new review for a lodge"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('rating') or not data.get('content'):
        return jsonify({'error': 'Rating and content are required'}), 400
    
    # Check rating range
    rating = float(data['rating'])
    if rating < 1 or rating > 5:
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    
    # Create review
    review = Review(
        lodge_id=lodge_id,
        author_id=current_user_id,
        rating=rating,
        title=data.get('title', ''),
        content=data['content'],
        verified_booking=data.get('verified_booking', False),
        is_approved=(user.is_admin or user.is_deputy)  # Auto-approve for admins/deputies
    )
    
    db.session.add(review)
    db.session.commit()
    
    return jsonify({
        'message': 'Review submitted successfully',
        'review': review_to_dict(review)
    }), 201

@reviews_bp.route('/reviews/<int:review_id>', methods=['GET'])
def get_review(review_id):
    """Get a specific review"""
    review = Review.query.get(review_id)
    
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    return jsonify({'review': review_to_dict(review)}), 200

@reviews_bp.route('/reviews/<int:review_id>', methods=['PUT'])
@jwt_required()
def update_review(review_id):
    """Update a review"""
    current_user_id = get_jwt_identity()
    review = Review.query.get(review_id)
    
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    # Check permission
    user = User.query.get(current_user_id)
    if review.author_id != current_user_id and not (user.is_admin or user.is_deputy):
        return jsonify({'error': 'Not authorized'}), 403
    
    data = request.get_json()
    
    # Update fields
    if 'rating' in data:
        review.rating = float(data['rating'])
    if 'title' in data:
        review.title = data['title']
    if 'content' in data:
        review.content = data['content']
    if 'verified_booking' in data:
        review.verified_booking = bool(data['verified_booking'])
    
    # Admin/deputy can change approval status
    if user.is_admin or user.is_deputy:
        if 'is_approved' in data:
            review.is_approved = bool(data['is_approved'])
    
    review.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Review updated successfully',
        'review': review_to_dict(review)
    }), 200

@reviews_bp.route('/reviews/<int:review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id):
    """Delete a review"""
    current_user_id = get_jwt_identity()
    review = Review.query.get(review_id)
    
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    # Check permission
    user = User.query.get(current_user_id)
    if review.author_id != current_user_id and not (user.is_admin or user.is_deputy):
        return jsonify({'error': 'Not authorized'}), 403
    
    db.session.delete(review)
    db.session.commit()
    
    return jsonify({'message': 'Review deleted successfully'}), 200

# =============================================
# SAFARI PACKAGE REVIEWS ROUTES
# =============================================

@reviews_bp.route('/safari-packages/<int:package_id>/reviews', methods=['GET'])
def get_safari_reviews(package_id):
    """Get all reviews for a safari package"""
    reviews = SafariReview.query.filter_by(package_id=package_id, is_approved=True).all()
    return jsonify({
        'reviews': [review.to_dict() for review in reviews]
    }), 200

@reviews_bp.route('/safari-packages/<int:package_id>/reviews', methods=['POST'])
@jwt_required()
def create_safari_review(package_id):
    """Create a new review for a safari package"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    if not data.get('message'):
        return jsonify({'error': 'Message is required'}), 400
    
    # Create review
    review = SafariReview(
        package_id=package_id,
        author_id=current_user_id,
        message=data['message'],
        is_approved=(user.is_admin or user.is_deputy)  # Auto-approve for admins/deputies
    )
    
    db.session.add(review)
    db.session.commit()
    
    return jsonify({
        'message': 'Review submitted successfully',
        'review': review.to_dict()
    }), 201

@reviews_bp.route('/safari-reviews/<int:review_id>', methods=['GET'])
def get_safari_review(review_id):
    """Get a specific safari review"""
    review = SafariReview.query.get(review_id)
    
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    return jsonify({'review': review.to_dict()}), 200

@reviews_bp.route('/safari-reviews/<int:review_id>', methods=['PUT'])
@jwt_required()
def update_safari_review(review_id):
    """Update a safari review"""
    current_user_id = get_jwt_identity()
    review = SafariReview.query.get(review_id)
    
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    # Check permission
    user = User.query.get(current_user_id)
    if review.author_id != current_user_id and not (user.is_admin or user.is_deputy):
        return jsonify({'error': 'Not authorized'}), 403
    
    data = request.get_json()
    
    if 'message' in data:
        review.message = data['message']
    
    # Admin/deputy can change approval status
    if user.is_admin or user.is_deputy:
        if 'is_approved' in data:
            review.is_approved = bool(data['is_approved'])
    
    db.session.commit()
    
    return jsonify({
        'message': 'Review updated successfully',
        'review': review.to_dict()
    }), 200

@reviews_bp.route('/safari-reviews/<int:review_id>', methods=['DELETE'])
@jwt_required()
def delete_safari_review(review_id):
    """Delete a safari review"""
    current_user_id = get_jwt_identity()
    review = SafariReview.query.get(review_id)
    
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    # Check permission
    user = User.query.get(current_user_id)
    if review.author_id != current_user_id and not (user.is_admin or user.is_deputy):
        return jsonify({'error': 'Not authorized'}), 403
    
    db.session.delete(review)
    db.session.commit()
    
    return jsonify({'message': 'Review deleted successfully'}), 200