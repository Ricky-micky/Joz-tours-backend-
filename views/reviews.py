from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Review, Lodge, User, db
from datetime import datetime

reviews_bp = Blueprint('reviews', __name__)

def is_admin_or_deputy():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user and (user.is_admin or user.is_deputy)

@reviews_bp.route('/lodges/<int:lodge_id>/reviews', methods=['GET'])
def get_lodge_reviews(lodge_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get only approved reviews for public
    reviews = Review.query.filter_by(
        lodge_id=lodge_id, 
        is_approved=True,
        is_active=True
    ).order_by(Review.created_at.desc())\
     .paginate(page=page, per_page=per_page, error_out=False)
    
    # Calculate average rating
    lodge = Lodge.query.get(lodge_id)
    average_rating = lodge.rating if lodge else 0.0
    
    return jsonify({
        'reviews': [{
            'id': review.id,
            'rating': review.rating,
            'title': review.title,
            'excerpt': review.content[:100] + '...' if len(review.content) > 100 else review.content,
            'author': review.author.username,
            'helpful_count': review.helpful_count,
            'verified_booking': review.verified_booking,
            'created_at': review.created_at.isoformat()
        } for review in reviews.items],
        'average_rating': average_rating,
        'total': reviews.total,
        'pages': reviews.pages,
        'current_page': reviews.page
    }), 200

@reviews_bp.route('/<int:review_id>', methods=['GET'])
def get_review(review_id):
    review = Review.query.get(review_id)
    if not review or not review.is_active or (not review.is_approved and not is_admin_or_deputy()):
        return jsonify({'error': 'Review not found'}), 404
    
    return jsonify({
        'review': {
            'id': review.id,
            'rating': review.rating,
            'title': review.title,
            'content': review.content,
            'author': {
                'id': review.author.id,
                'username': review.author.username,
                'profile_picture': review.author.profile_picture
            },
            'lodge': {
                'id': review.lodge.id,
                'name': review.lodge.name
            },
            'images': review.images or [],
            'helpful_count': review.helpful_count,
            'verified_booking': review.verified_booking,
            'created_at': review.created_at.isoformat()
        }
    }), 200

@reviews_bp.route('/', methods=['POST'])
@jwt_required()
def create_review():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    required_fields = ['lodge_id', 'rating', 'content']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if user has already reviewed this lodge
    existing_review = Review.query.filter_by(
        lodge_id=data['lodge_id'],
        author_id=user_id,
        is_active=True
    ).first()
    
    if existing_review:
        return jsonify({'error': 'You have already reviewed this lodge'}), 400
    
    review = Review(
        lodge_id=data['lodge_id'],
        author_id=user_id,
        rating=min(5.0, max(1.0, float(data['rating']))),  # Ensure rating between 1-5
        title=data.get('title'),
        content=data['content'],
        images=data.get('images', []),
        verified_booking=data.get('verified_booking', False),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Reviews from regular users need approval
    user = User.query.get(user_id)
    if user.is_admin or user.is_deputy:
        review.is_approved = True
    
    db.session.add(review)
    db.session.commit()
    
    # Update lodge rating if review is approved
    if review.is_approved:
        update_lodge_rating(data['lodge_id'])
    
    return jsonify({
        'message': 'Review submitted successfully' + (' (pending approval)' if not review.is_approved else ''),
        'review': {
            'id': review.id,
            'is_approved': review.is_approved
        }
    }), 201

@reviews_bp.route('/<int:review_id>', methods=['PUT'])
@jwt_required()
def update_review(review_id):
    review = Review.query.get(review_id)
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Check if user is author
    if review.author_id != user_id and not (user.is_admin or user.is_deputy):
        return jsonify({'error': 'Unauthorized to edit this review'}), 403
    
    data = request.get_json()
    
    if 'rating' in data:
        review.rating = min(5.0, max(1.0, float(data['rating'])))
    
    if 'title' in data:
        review.title = data['title']
    
    if 'content' in data:
        review.content = data['content']
    
    if 'images' in data:
        review.images = data['images']
    
    review.updated_at = datetime.utcnow()
    
    # If admin/deputy edits, keep it approved
    if user.is_admin or user.is_deputy:
        review.is_approved = True
    
    db.session.commit()
    
    # Update lodge rating
    update_lodge_rating(review.lodge_id)
    
    return jsonify({
        'message': 'Review updated successfully',
        'review': {
            'id': review.id,
            'rating': review.rating
        }
    }), 200

@reviews_bp.route('/<int:review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id):
    review = Review.query.get(review_id)
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Check if user is author or admin/deputy
    if review.author_id != user_id and not (user.is_admin or user.is_deputy):
        return jsonify({'error': 'Unauthorized to delete this review'}), 403
    
    # Store lodge_id for rating update
    lodge_id = review.lodge_id
    
    # Soft delete
    review.is_active = False
    db.session.commit()
    
    # Update lodge rating
    update_lodge_rating(lodge_id)
    
    return jsonify({'message': 'Review deleted successfully'}), 200

@reviews_bp.route('/<int:review_id>/helpful', methods=['POST'])
@jwt_required()
def mark_helpful(review_id):
    review = Review.query.get(review_id)
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    review.helpful_count += 1
    db.session.commit()
    
    return jsonify({
        'message': 'Marked as helpful',
        'helpful_count': review.helpful_count
    }), 200

def update_lodge_rating(lodge_id):
    """Update the average rating for a lodge"""
    reviews = Review.query.filter_by(
        lodge_id=lodge_id,
        is_approved=True,
        is_active=True
    ).all()
    
    if reviews:
        total_rating = sum([review.rating for review in reviews])
        average_rating = total_rating / len(reviews)
        
        lodge = Lodge.query.get(lodge_id)
        lodge.rating = round(average_rating, 1)
        db.session.commit()