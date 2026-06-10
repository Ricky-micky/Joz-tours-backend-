from flask import Blueprint, request, jsonify
from datetime import datetime
from models import SafariComment, SafariReview, User
from extensions import db

# Create Blueprint
safari_comment_bp = Blueprint('safari_comments', __name__)

# CREATE - Add a new safari comment
@safari_comment_bp.route('/safari-comments', methods=['POST'])
def create_safari_comment():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['review_id', 'author_id', 'message']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Verify review exists
        review = SafariReview.query.get(data['review_id'])
        if not review:
            return jsonify({'error': 'Review not found'}), 404
        
        # Verify author exists
        author = User.query.get(data['author_id'])
        if not author:
            return jsonify({'error': 'Author not found'}), 404
        
        # Create new safari comment
        safari_comment = SafariComment(
            review_id=data['review_id'],
            author_id=data['author_id'],
            message=data['message'],
            is_approved=data.get('is_approved', True),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(safari_comment)
        db.session.commit()
        
        return jsonify({
            'message': 'Safari comment created successfully',
            'data': safari_comment.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# READ - Get all safari comments
@safari_comment_bp.route('/safari-comments', methods=['GET'])
def get_all_safari_comments():
    try:
        # Get query parameters for filtering
        review_id = request.args.get('review_id')
        author_id = request.args.get('author_id')
        is_approved = request.args.get('is_approved')
        is_active = request.args.get('is_active')
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        query = SafariComment.query
        
        if review_id:
            query = query.filter_by(review_id=int(review_id))
        
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
        query = query.order_by(SafariComment.created_at.asc())
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        safari_comments = query.all()
        
        return jsonify({
            'count': len(safari_comments),
            'total': total_count,
            'offset': offset,
            'limit': limit if limit else 'none',
            'data': [comment.to_dict() for comment in safari_comments]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Get single safari comment by ID
@safari_comment_bp.route('/safari-comments/<int:comment_id>', methods=['GET'])
def get_safari_comment(comment_id):
    try:
        safari_comment = SafariComment.query.get_or_404(comment_id)
        
        return jsonify({
            'data': safari_comment.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# UPDATE - Update a safari comment
@safari_comment_bp.route('/safari-comments/<int:comment_id>', methods=['PUT'])
def update_safari_comment(comment_id):
    try:
        safari_comment = SafariComment.query.get_or_404(comment_id)
        data = request.get_json()
        
        # Update fields if provided
        if 'message' in data:
            safari_comment.message = data['message']
        if 'is_approved' in data:
            safari_comment.is_approved = data['is_approved']
        if 'is_active' in data:
            safari_comment.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Safari comment updated successfully',
            'data': safari_comment.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# DELETE - Delete a safari comment
@safari_comment_bp.route('/safari-comments/<int:comment_id>', methods=['DELETE'])
def delete_safari_comment(comment_id):
    try:
        safari_comment = SafariComment.query.get_or_404(comment_id)
        
        db.session.delete(safari_comment)
        db.session.commit()
        
        return jsonify({
            'message': 'Safari comment deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get comments for a specific review
@safari_comment_bp.route('/safari-reviews/<int:review_id>/comments', methods=['GET'])
def get_review_comments(review_id):
    try:
        # Verify review exists
        review = SafariReview.query.get_or_404(review_id)
        
        is_approved = request.args.get('is_approved', 'true')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = SafariComment.query.filter_by(review_id=review_id)
        
        if is_approved.lower() in ['true', '1', 'yes']:
            query = query.filter_by(is_approved=True)
        
        query = query.filter_by(is_active=True)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        comments = query.order_by(SafariComment.created_at.asc())\
                       .offset(offset)\
                       .limit(limit)\
                       .all()
        
        return jsonify({
            'review_id': review_id,
            'review_message': review.message[:100] + '...' if len(review.message) > 100 else review.message,
            'count': len(comments),
            'total': total_count,
            'data': [comment.to_dict() for comment in comments]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get comments by a specific user
@safari_comment_bp.route('/users/<int:user_id>/comments', methods=['GET'])
def get_user_comments(user_id):
    try:
        # Verify user exists
        user = User.query.get_or_404(user_id)
        
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = SafariComment.query.filter_by(author_id=user_id)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        comments = query.order_by(SafariComment.created_at.desc())\
                       .offset(offset)\
                       .limit(limit)\
                       .all()
        
        return jsonify({
            'user_id': user_id,
            'username': user.username,
            'count': len(comments),
            'total': total_count,
            'data': [comment.to_dict() for comment in comments]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Toggle comment approval status
@safari_comment_bp.route('/safari-comments/<int:comment_id>/toggle-approval', methods=['PATCH'])
def toggle_comment_approval(comment_id):
    try:
        safari_comment = SafariComment.query.get_or_404(comment_id)
        
        safari_comment.is_approved = not safari_comment.is_approved
        
        db.session.commit()
        
        status = "approved" if safari_comment.is_approved else "unapproved"
        
        return jsonify({
            'message': f'Comment {status} successfully',
            'data': safari_comment.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Toggle comment active status
@safari_comment_bp.route('/safari-comments/<int:comment_id>/toggle-active', methods=['PATCH'])
def toggle_comment_active(comment_id):
    try:
        safari_comment = SafariComment.query.get_or_404(comment_id)
        
        safari_comment.is_active = not safari_comment.is_active
        
        db.session.commit()
        
        status = "activated" if safari_comment.is_active else "deactivated"
        
        return jsonify({
            'message': f'Comment {status} successfully',
            'data': safari_comment.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Reply to a comment (nested comments support)
@safari_comment_bp.route('/safari-comments/<int:comment_id>/reply', methods=['POST'])
def reply_to_comment(comment_id):
    try:
        parent_comment = SafariComment.query.get_or_404(comment_id)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['author_id', 'message']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Verify author exists
        author = User.query.get(data['author_id'])
        if not author:
            return jsonify({'error': 'Author not found'}), 404
        
        # Create reply comment
        reply_comment = SafariComment(
            review_id=parent_comment.review_id,
            author_id=data['author_id'],
            message=data['message'],
            is_approved=data.get('is_approved', True),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(reply_comment)
        db.session.commit()
        
        return jsonify({
            'message': 'Reply created successfully',
            'data': reply_comment.to_dict(),
            'parent_comment_id': parent_comment.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Bulk create safari comments
@safari_comment_bp.route('/safari-comments/bulk', methods=['POST'])
def create_bulk_safari_comments():
    try:
        data = request.get_json()
        
        if not isinstance(data, list):
            return jsonify({'error': 'Request body must be an array of safari comments'}), 400
        
        created_comments = []
        
        for comment_data in data:
            # Validate required fields for each comment
            required_fields = ['review_id', 'author_id', 'message']
            missing_fields = [field for field in required_fields if field not in comment_data]
            
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields in one of the items: {", ".join(missing_fields)}'
                }), 400
            
            # Verify review exists
            review = SafariReview.query.get(comment_data['review_id'])
            if not review:
                continue  # Skip if review doesn't exist
            
            # Verify author exists
            author = User.query.get(comment_data['author_id'])
            if not author:
                continue  # Skip if author doesn't exist
            
            safari_comment = SafariComment(
                review_id=comment_data['review_id'],
                author_id=comment_data['author_id'],
                message=comment_data['message'],
                is_approved=comment_data.get('is_approved', True),
                is_active=comment_data.get('is_active', True)
            )
            
            db.session.add(safari_comment)
            created_comments.append(safari_comment)
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_comments)} safari comments created successfully',
            'data': [comment.to_dict() for comment in created_comments]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Search comments by message content
@safari_comment_bp.route('/safari-comments/search', methods=['GET'])
def search_safari_comments():
    try:
        search_term = request.args.get('q', '')
        review_id = request.args.get('review_id')
        is_approved = request.args.get('is_approved', 'true')
        
        if not search_term:
            return jsonify({'error': 'Search term is required'}), 400
        
        query = SafariComment.query
        
        query = query.filter(SafariComment.message.ilike(f'%{search_term}%'))
        
        if review_id:
            query = query.filter_by(review_id=int(review_id))
        
        if is_approved.lower() in ['true', '1', 'yes']:
            query = query.filter_by(is_approved=True)
        
        query = query.filter_by(is_active=True)\
                     .order_by(SafariComment.created_at.desc())
        
        comments = query.all()
        
        return jsonify({
            'count': len(comments),
            'search_term': search_term,
            'data': [comment.to_dict() for comment in comments]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get latest comments
@safari_comment_bp.route('/safari-comments/latest', methods=['GET'])
def get_latest_comments():
    try:
        limit = request.args.get('limit', 10, type=int)
        
        comments = SafariComment.query.filter_by(
            is_approved=True,
            is_active=True
        ).order_by(SafariComment.created_at.desc())\
         .limit(limit)\
         .all()
        
        return jsonify({
            'count': len(comments),
            'data': [comment.to_dict() for comment in comments]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get comment statistics
@safari_comment_bp.route('/safari-comments/stats', methods=['GET'])
def get_comment_stats():
    try:
        review_id = request.args.get('review_id')
        author_id = request.args.get('author_id')
        
        query = SafariComment.query
        
        if review_id:
            query = query.filter_by(review_id=int(review_id))
        
        if author_id:
            query = query.filter_by(author_id=int(author_id))
        
        # Get counts
        total_comments = query.count()
        approved_comments = query.filter_by(is_approved=True).count()
        active_comments = query.filter_by(is_active=True).count()
        
        # Get latest comment date
        latest_comment = query.order_by(SafariComment.created_at.desc()).first()
        latest_date = latest_comment.created_at if latest_comment else None
        
        stats = {
            'total_comments': total_comments,
            'approved_comments': approved_comments,
            'active_comments': active_comments,
            'pending_comments': total_comments - approved_comments,
            'latest_comment_date': latest_date.isoformat() if latest_date else None
        }
        
        if review_id:
            stats['review_id'] = review_id
        
        if author_id:
            stats['author_id'] = author_id
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get comments for a specific package (through review)
@safari_comment_bp.route('/packages/<int:package_id>/comments', methods=['GET'])
def get_package_comments(package_id):
    try:
        # Verify package exists
        package = SafariPackage.query.get_or_404(package_id)
        
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get all review IDs for this package
        review_ids = [review.id for review in package.reviews]
        
        if not review_ids:
            return jsonify({
                'package_id': package_id,
                'package_name': package.name,
                'count': 0,
                'data': []
            })
        
        # Get comments for these reviews
        query = SafariComment.query.filter(SafariComment.review_id.in_(review_ids))
        query = query.filter_by(is_approved=True, is_active=True)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        comments = query.order_by(SafariComment.created_at.desc())\
                       .offset(offset)\
                       .limit(limit)\
                       .all()
        
        return jsonify({
            'package_id': package_id,
            'package_name': package.name,
            'count': len(comments),
            'total': total_count,
            'data': [comment.to_dict() for comment in comments]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500