from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, Review, Story, LodgePrice, AdminActionLog, db
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

def is_admin():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user and user.is_admin

def is_admin_or_deputy():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user and (user.is_admin or user.is_deputy)

def log_admin_action(admin_id, action_type, resource_type, resource_id, details=None):
    """Log admin actions for audit trail"""
    log = AdminActionLog(
        admin_id=admin_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        created_at=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()

@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def admin_dashboard():
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get statistics
    total_users = User.query.count()
    total_reviews = Review.query.count()
    total_stories = Story.query.count()
    pending_reviews = Review.query.filter_by(is_approved=False, is_active=True).count()
    
    return jsonify({
        'statistics': {
            'total_users': total_users,
            'total_reviews': total_reviews,
            'total_stories': total_stories,
            'pending_reviews': pending_reviews
        }
    }), 200

@admin_bp.route('/reviews/pending', methods=['GET'])
@jwt_required()
def get_pending_reviews():
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    pending_reviews = Review.query.filter_by(is_approved=False, is_active=True)\
        .order_by(Review.created_at.desc())\
        .all()
    
    return jsonify({
        'reviews': [{
            'id': review.id,
            'rating': review.rating,
            'title': review.title,
            'excerpt': review.content[:150] + '...' if len(review.content) > 150 else review.content,
            'author': review.author.username,
            'lodge': review.lodge.name,
            'created_at': review.created_at.isoformat()
        } for review in pending_reviews]
    }), 200

@admin_bp.route('/reviews/<int:review_id>/approve', methods=['PUT'])
@jwt_required()
def approve_review(review_id):
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    review = Review.query.get(review_id)
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    review.is_approved = True
    db.session.commit()
    
    # Log action
    user_id = get_jwt_identity()
    log_admin_action(user_id, 'approve', 'review', review_id)
    
    # Update lodge rating
    from .reviews import update_lodge_rating
    update_lodge_rating(review.lodge_id)
    
    return jsonify({'message': 'Review approved successfully'}), 200

@admin_bp.route('/reviews/<int:review_id>/reject', methods=['PUT'])
@jwt_required()
def reject_review(review_id):
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    review = Review.query.get(review_id)
    if not review:
        return jsonify({'error': 'Review not found'}), 404
    
    # Soft delete the review
    review.is_active = False
    review.is_approved = False
    db.session.commit()
    
    # Log action
    user_id = get_jwt_identity()
    log_admin_action(user_id, 'reject', 'review', review_id, {
        'reason': request.json.get('reason', 'Review rejected')
    })
    
    return jsonify({'message': 'Review rejected and removed'}), 200

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    if not is_admin():
        return jsonify({'error': 'Only admins can view all users'}), 403
    
    users = User.query.all()
    return jsonify({
        'users': [user.to_dict() for user in users]
    }), 200

@admin_bp.route('/users/<int:user_id>/toggle', methods=['PUT'])
@jwt_required()
def toggle_user_status(user_id):
    if not is_admin():
        return jsonify({'error': 'Only admins can change user status'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Prevent deactivating other admins
    current_admin_id = get_jwt_identity()
    if user.id == current_admin_id:
        return jsonify({'error': 'Cannot deactivate yourself'}), 400
    
    if user.is_admin:
        return jsonify({'error': 'Cannot deactivate another admin'}), 400
    
    user.is_active = not user.is_active
    db.session.commit()
    
    # Log action
    log_admin_action(current_admin_id, 'toggle_status', 'user', user_id, {
        'new_status': 'active' if user.is_active else 'inactive'
    })
    
    return jsonify({
        'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
        'is_active': user.is_active
    }), 200

@admin_bp.route('/logs', methods=['GET'])
@jwt_required()
def get_admin_logs():
    if not is_admin():
        return jsonify({'error': 'Only admins can view logs'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    logs = AdminActionLog.query\
        .order_by(AdminActionLog.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'logs': [{
            'id': log.id,
            'admin': log.admin.username,
            'action_type': log.action_type,
            'resource_type': log.resource_type,
            'resource_id': log.resource_id,
            'details': log.details,
            'created_at': log.created_at.isoformat()
        } for log in logs.items],
        'total': logs.total,
        'pages': logs.pages,
        'current_page': logs.page
    }), 200