from flask import Blueprint, request, jsonify
from datetime import datetime
from models import SafariReview, SafariPackage, User, SafariComment
from extensions import db

# Create Blueprint
safari_review_bp = Blueprint('safari_reviews', __name__)

# CREATE - Add a new safari review
@safari_review_bp.route('/safari-reviews', methods=['POST'])
def create_safari_review():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['package_id', 'author_id', 'message']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Check if user has already reviewed this package
        existing_review = SafariReview.query.filter_by(
            package_id=data['package_id'],
            author_id=data['author_id']
        ).first()
        
        if existing_review:
            return jsonify({'error': 'You have already reviewed this package'}), 409
        
        # Create new safari review
        safari_review = SafariReview(
            package_id=data['package_id'],
            author_id=data['author_id'],
            message=data['message'],
            is_approved=data.get('is_approved', True),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(safari_review)
        db.session.commit()
        
        return jsonify({
            'message': 'Safari review created successfully',
            'data': safari_review.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# READ - Get all safari reviews
@safari_review_bp.route('/safari-reviews', methods=['GET'])
def get_all_safari_reviews():
    try:
        # Get query parameters for filtering
        package_id = request.args.get('package_id')
        author_id = request.args.get('author_id')
        is_approved = request.args.get('is_approved')
        is_active = request.args.get('is_active')
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        query = SafariReview.query
        
        if package_id:
            query = query.filter_by(package_id=int(package_id))
        
        if author_id:
            query = query.filter_by(author_id=int(author_id))
        
        if is_approved is not None:
            is_approved_bool = is_approved.lower() in ['true', '1', 'yes']
            query = query.filter_by(is_approved=is_approved_bool)
        
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']
            query = query.filter_by(is_active=is_active_bool)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply ordering and pagination
        query = query.order_by(SafariReview.created_at.desc())
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        safari_reviews = query.all()
        
        return jsonify({
            'count': len(safari_reviews),
            'total': total_count,
            'offset': offset,
            'limit': limit if limit else 'none',
            'data': [review.to_dict() for review in safari_reviews]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Get single safari review by ID
@safari_review_bp.route('/safari-reviews/<int:review_id>', methods=['GET'])
def get_safari_review(review_id):
    try:
        safari_review = SafariReview.query.get_or_404(review_id)
        
        return jsonify({
            'data': safari_review.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# UPDATE - Update a safari review
@safari_review_bp.route('/safari-reviews/<int:review_id>', methods=['PUT'])
def update_safari_review(review_id):
    try:
        safari_review = SafariReview.query.get_or_404(review_id)
        data = request.get_json()
        
        # Update fields if provided
        if 'message' in data:
            safari_review.message = data['message']
        if 'is_approved' in data:
            safari_review.is_approved = data['is_approved']
        if 'is_active' in data:
            safari_review.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Safari review updated successfully',
            'data': safari_review.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# DELETE - Delete a safari review
@safari_review_bp.route('/safari-reviews/<int:review_id>', methods=['DELETE'])
def delete_safari_review(review_id):
    try:
        safari_review = SafariReview.query.get_or_404(review_id)
        
        db.session.delete(safari_review)
        db.session.commit()
        
        return jsonify({
            'message': 'Safari review deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get reviews for a specific package
@safari_review_bp.route('/packages/<int:package_id>/reviews', methods=['GET'])
def get_package_reviews(package_id):
    try:
        # Verify package exists
        package = SafariPackage.query.get_or_404(package_id)
        
        is_approved = request.args.get('is_approved', 'true')
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = SafariReview.query.filter_by(package_id=package_id)
        
        if is_approved.lower() in ['true', '1', 'yes']:
            query = query.filter_by(is_approved=True)
        
        query = query.filter_by(is_active=True)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        reviews = query.order_by(SafariReview.created_at.desc())\
                      .offset(offset)\
                      .limit(limit)\
                      .all()
        
        return jsonify({
            'package_id': package_id,
            'package_name': package.name,
            'count': len(reviews),
            'total': total_count,
            'average_rating': 0,  # You can add rating field later
            'data': [review.to_dict() for review in reviews]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get reviews by a specific user
@safari_review_bp.route('/users/<int:user_id>/reviews', methods=['GET'])
def get_user_reviews(user_id):
    try:
        # Verify user exists
        user = User.query.get_or_404(user_id)
        
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = SafariReview.query.filter_by(author_id=user_id)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        reviews = query.order_by(SafariReview.created_at.desc())\
                      .offset(offset)\
                      .limit(limit)\
                      .all()
        
        return jsonify({
            'user_id': user_id,
            'username': user.username,
            'count': len(reviews),
            'total': total_count,
            'data': [review.to_dict() for review in reviews]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Toggle review approval status
@safari_review_bp.route('/safari-reviews/<int:review_id>/toggle-approval', methods=['PATCH'])
def toggle_review_approval(review_id):
    try:
        safari_review = SafariReview.query.get_or_404(review_id)
        
        safari_review.is_approved = not safari_review.is_approved
        
        db.session.commit()
        
        status = "approved" if safari_review.is_approved else "unapproved"
        
        return jsonify({
            'message': f'Review {status} successfully',
            'data': safari_review.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Toggle review active status
@safari_review_bp.route('/safari-reviews/<int:review_id>/toggle-active', methods=['PATCH'])
def toggle_review_active(review_id):
    try:
        safari_review = SafariReview.query.get_or_404(review_id)
        
        safari_review.is_active = not safari_review.is_active
        
        db.session.commit()
        
        status = "activated" if safari_review.is_active else "deactivated"
        
        return jsonify({
            'message': f'Review {status} successfully',
            'data': safari_review.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get review with comments
@safari_review_bp.route('/safari-reviews/<int:review_id>/with-comments', methods=['GET'])
def get_review_with_comments(review_id):
    try:
        safari_review = SafariReview.query.get_or_404(review_id)
        
        # Load review data
        review_data = safari_review.to_dict()
        
        # Get comments for this review
        comments = SafariComment.query.filter_by(
            review_id=review_id,
            is_approved=True,
            is_active=True
        ).order_by(SafariComment.created_at.asc()).all()
        
        review_data['comments'] = [comment.to_dict() for comment in comments]
        
        return jsonify({
            'data': review_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# Bulk create safari reviews
@safari_review_bp.route('/safari-reviews/bulk', methods=['POST'])
def create_bulk_safari_reviews():
    try:
        data = request.get_json()
        
        if not isinstance(data, list):
            return jsonify({'error': 'Request body must be an array of safari reviews'}), 400
        
        created_reviews = []
        
        for review_data in data:
            # Validate required fields for each review
            required_fields = ['package_id', 'author_id', 'message']
            missing_fields = [field for field in required_fields if field not in review_data]
            
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields in one of the items: {", ".join(missing_fields)}'
                }), 400
            
            # Check if user has already reviewed this package
            existing_review = SafariReview.query.filter_by(
                package_id=review_data['package_id'],
                author_id=review_data['author_id']
            ).first()
            
            if existing_review:
                continue  # Skip duplicates
            
            safari_review = SafariReview(
                package_id=review_data['package_id'],
                author_id=review_data['author_id'],
                message=review_data['message'],
                is_approved=review_data.get('is_approved', True),
                is_active=review_data.get('is_active', True)
            )
            
            db.session.add(safari_review)
            created_reviews.append(safari_review)
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_reviews)} safari reviews created successfully',
            'data': [review.to_dict() for review in created_reviews]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Search reviews by message content
@safari_review_bp.route('/safari-reviews/search', methods=['GET'])
def search_safari_reviews():
    try:
        search_term = request.args.get('q', '')
        package_id = request.args.get('package_id')
        is_approved = request.args.get('is_approved', 'true')
        
        if not search_term:
            return jsonify({'error': 'Search term is required'}), 400
        
        query = SafariReview.query
        
        query = query.filter(SafariReview.message.ilike(f'%{search_term}%'))
        
        if package_id:
            query = query.filter_by(package_id=int(package_id))
        
        if is_approved.lower() in ['true', '1', 'yes']:
            query = query.filter_by(is_approved=True)
        
        query = query.filter_by(is_active=True)\
                     .order_by(SafariReview.created_at.desc())
        
        reviews = query.all()
        
        return jsonify({
            'count': len(reviews),
            'search_term': search_term,
            'data': [review.to_dict() for review in reviews]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get latest reviews
@safari_review_bp.route('/safari-reviews/latest', methods=['GET'])
def get_latest_reviews():
    try:
        limit = request.args.get('limit', 5, type=int)
        
        reviews = SafariReview.query.filter_by(
            is_approved=True,
            is_active=True
        ).order_by(SafariReview.created_at.desc())\
         .limit(limit)\
         .all()
        
        return jsonify({
            'count': len(reviews),
            'data': [review.to_dict() for review in reviews]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get review statistics
@safari_review_bp.route('/safari-reviews/stats', methods=['GET'])
def get_review_stats():
    try:
        package_id = request.args.get('package_id')
        
        query = SafariReview.query
        
        if package_id:
            query = query.filter_by(package_id=int(package_id))
        
        # Get counts
        total_reviews = query.count()
        approved_reviews = query.filter_by(is_approved=True).count()
        active_reviews = query.filter_by(is_active=True).count()
        
        # Get latest review date
        latest_review = query.order_by(SafariReview.created_at.desc()).first()
        latest_date = latest_review.created_at if latest_review else None
        
        stats = {
            'total_reviews': total_reviews,
            'approved_reviews': approved_reviews,
            'active_reviews': active_reviews,
            'pending_reviews': total_reviews - approved_reviews,
            'latest_review_date': latest_date.isoformat() if latest_date else None
        }
        
        if package_id:
            stats['package_id'] = package_id
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500