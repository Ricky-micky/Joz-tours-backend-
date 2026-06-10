from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models import User, db

users_bp = Blueprint('users', __name__)

def is_admin_or_deputy():
    """Check if current user is admin or deputy"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user and (user.is_admin or user.is_deputy)

def get_current_user():
    """Get current user from JWT"""
    user_id = get_jwt_identity()
    return User.query.get(user_id)

# ========== AUTHENTICATION ROUTES ==========

@users_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    # Validation
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if username exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    # Check if email exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    # Create new user
    new_user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        phone=data.get('phone'),
        is_admin=data.get('is_admin', False),
        is_deputy=data.get('is_deputy', False),
        is_active=True
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    # Create access token
    access_token = create_access_token(
        identity=new_user.id,
        expires_delta=timedelta(hours=24)
    )
    
    return jsonify({
        'message': 'User registered successfully',
        'access_token': access_token,
        'user': new_user.to_dict()
    }), 201

@users_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is inactive'}), 403
    
    # Create access token
    access_token = create_access_token(
        identity=user.id,
        expires_delta=timedelta(hours=24)
    )
    
    return jsonify({
        'access_token': access_token,
        'token_type': 'bearer',
        'expires_in': 86400,  # 24 hours in seconds
        'user': user.to_dict()
    }), 200

@users_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 404
    
    access_token = create_access_token(identity=user_id)
    
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

# ========== USER PROFILE ROUTES ==========

@users_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    """Get current user's profile"""
    user = get_current_user()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200

@users_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_current_user_profile():
    """Update current user's profile"""
    user = get_current_user()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update username if provided and unique
    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 400
        user.username = data['username']
    
    # Update email if provided and unique
    if 'email' in data and data['email'] != user.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        user.email = data['email']
    
    # Update phone if provided
    if 'phone' in data:
        user.phone = data['phone']
    
    # Update password if provided
    if 'password' in data:
        user.password_hash = generate_password_hash(data['password'])
    
    db.session.commit()
    
    return jsonify({
        'message': 'Profile updated successfully',
        'user': user.to_dict()
    }), 200

@users_bp.route('/me/password', methods=['PUT'])
@jwt_required()
def change_password():
    """Change current user's password"""
    user = get_current_user()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    required_fields = ['current_password', 'new_password']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Verify current password
    if not check_password_hash(user.password_hash, data['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    # Update to new password
    user.password_hash = generate_password_hash(data['new_password'])
    db.session.commit()
    
    return jsonify({'message': 'Password updated successfully'}), 200

# ========== USER MANAGEMENT ROUTES ==========

@users_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_users():
    """Get all users (admin/deputy only)"""
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    is_active = request.args.get('is_active', type=str)
    role = request.args.get('role', type=str)  # admin, deputy, regular
    
    # Build query
    query = User.query
    
    # Filter by active status
    if is_active is not None:
        if is_active.lower() == 'true':
            query = query.filter_by(is_active=True)
        elif is_active.lower() == 'false':
            query = query.filter_by(is_active=False)
    
    # Filter by role
    if role:
        if role == 'admin':
            query = query.filter_by(is_admin=True)
        elif role == 'deputy':
            query = query.filter_by(is_deputy=True, is_admin=False)
        elif role == 'regular':
            query = query.filter_by(is_admin=False, is_deputy=False)
    
    # Paginate
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'users': [user.to_dict() for user in users.items],
        'total': users.total,
        'page': users.page,
        'per_page': users.per_page,
        'pages': users.pages
    }), 200

@users_bp.route('/search', methods=['GET'])
@jwt_required()
def search_users():
    """Search users by username or email (admin/deputy only)"""
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    search_term = request.args.get('q', '')
    
    if not search_term or len(search_term) < 2:
        return jsonify({'error': 'Search term must be at least 2 characters'}), 400
    
    users = User.query.filter(
        (User.username.ilike(f'%{search_term}%')) |
        (User.email.ilike(f'%{search_term}%'))
    ).filter_by(is_active=True).limit(20).all()
    
    return jsonify({
        'users': [user.to_dict() for user in users],
        'count': len(users)
    }), 200

@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Get user by ID"""
    current_user = get_current_user()
    
    # Users can view their own profile, admins/deputies can view any
    if current_user.id != user_id and not (current_user.is_admin or current_user.is_deputy):
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200

@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Update user (admin/deputy can update any, users can update themselves)"""
    current_user = get_current_user()
    
    # Check permissions
    if current_user.id != user_id and not (current_user.is_admin or current_user.is_deputy):
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Basic field updates (allowed for self or admin/deputy)
    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 400
        user.username = data['username']
    
    if 'email' in data and data['email'] != user.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        user.email = data['email']
    
    if 'phone' in data:
        user.phone = data['phone']
    
    # Only admins can change these fields
    if current_user.is_admin:
        if 'is_admin' in data:
            user.is_admin = data['is_admin']
        if 'is_deputy' in data:
            user.is_deputy = data['is_deputy']
        if 'is_active' in data:
            user.is_active = data['is_active']
    
    # Admin can set password for user
    if current_user.is_admin and 'password' in data:
        user.password_hash = generate_password_hash(data['password'])
    
    db.session.commit()
    
    return jsonify({
        'message': 'User updated successfully',
        'user': user.to_dict()
    }), 200

@users_bp.route('/<int:user_id>/toggle-active', methods=['PUT'])
@jwt_required()
def toggle_user_active(user_id):
    """Toggle user active status (admin only)"""
    current_user = get_current_user()
    
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can change user status'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Cannot deactivate yourself
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400
    
    user.is_active = not user.is_active
    action = 'activated' if user.is_active else 'deactivated'
    
    db.session.commit()
    
    return jsonify({
        'message': f'User {user.username} has been {action}',
        'user': user.to_dict()
    }), 200

@users_bp.route('/<int:user_id>/make-deputy', methods=['PUT'])
@jwt_required()
def make_deputy(user_id):
    """Make user a deputy admin (admin only)"""
    current_user = get_current_user()
    
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can assign deputy roles'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.is_deputy:
        return jsonify({'error': 'User is already a deputy'}), 400
    
    user.is_deputy = True
    db.session.commit()
    
    return jsonify({
        'message': f'User {user.username} is now a deputy admin',
        'user': user.to_dict()
    }), 200

@users_bp.route('/<int:user_id>/remove-deputy', methods=['PUT'])
@jwt_required()
def remove_deputy(user_id):
    """Remove deputy role from user (admin only)"""
    current_user = get_current_user()
    
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can remove deputy roles'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if not user.is_deputy:
        return jsonify({'error': 'User is not a deputy'}), 400
    
    # Cannot remove your own deputy role if you're not admin
    if user.id == current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Cannot remove your own deputy role'}), 400
    
    user.is_deputy = False
    db.session.commit()
    
    return jsonify({
        'message': f'Deputy role removed from {user.username}',
        'user': user.to_dict()
    }), 200

@users_bp.route('/<int:user_id>/stats', methods=['GET'])
@jwt_required()
def get_user_stats(user_id):
    """Get user statistics (reviews, comments, etc.)"""
    current_user = get_current_user()
    
    # Users can view their own stats, admins/deputies can view any
    if current_user.id != user_id and not (current_user.is_admin or current_user.is_deputy):
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    stats = {
        'comments_count': len(user.comments),
        'stories_count': len(user.stories),
        'reviews_count': len(user.reviews),
        'safari_reviews_count': len(user.safari_reviews),
        'safari_comments_count': len(user.safari_comments),
        'price_edits_count': len(user.price_histories),
        'account_created': user.created_at.isoformat(),
        'is_active': user.is_active,
        'is_admin': user.is_admin,
        'is_deputy': user.is_deputy
    }
    
    return jsonify({'stats': stats}), 200

# ========== USER ACTIVITY ROUTES ==========

@users_bp.route('/me/comments', methods=['GET'])
@jwt_required()
def get_my_comments():
    """Get current user's comments"""
    user = get_current_user()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    comments = Comment.query.filter_by(user_id=user.id, is_active=True)\
        .order_by(Comment.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'comments': [comment.to_dict() for comment in comments.items],
        'total': comments.total,
        'page': comments.page,
        'per_page': comments.per_page
    }), 200

@users_bp.route('/me/reviews', methods=['GET'])
@jwt_required()
def get_my_reviews():
    """Get current user's reviews"""
    user = get_current_user()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    reviews = Review.query.filter_by(author_id=user.id, is_active=True)\
        .order_by(Review.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'reviews': [review.to_dict() for review in reviews.items],
        'total': reviews.total,
        'page': reviews.page,
        'per_page': reviews.per_page
    }), 200

@users_bp.route('/<int:user_id>/activity', methods=['GET'])
@jwt_required()
def get_user_activity(user_id):
    """Get user activity feed (admin/deputy only or self)"""
    current_user = get_current_user()
    
    if current_user.id != user_id and not (current_user.is_admin or current_user.is_deputy):
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    limit = request.args.get('limit', 50, type=int)
    
    # Get recent activity (could be expanded based on your needs)
    activity = []
    
    # Add recent reviews
    recent_reviews = Review.query.filter_by(author_id=user.id)\
        .order_by(Review.created_at.desc())\
        .limit(10).all()
    for review in recent_reviews:
        activity.append({
            'type': 'review',
            'data': review.to_dict(),
            'timestamp': review.created_at.isoformat()
        })
    
    # Add recent comments
    recent_comments = Comment.query.filter_by(user_id=user.id)\
        .order_by(Comment.created_at.desc())\
        .limit(10).all()
    for comment in recent_comments:
        activity.append({
            'type': 'comment',
            'data': comment.to_dict(),
            'timestamp': comment.created_at.isoformat()
        })
    
    # Sort by timestamp
    activity.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({
        'activity': activity[:limit],
        'user': user.to_dict()
    }), 200

# ========== ADMIN-ONLY ROUTES ==========

@users_bp.route('/admins', methods=['GET'])
@jwt_required()
def get_admins():
    """Get all admin users (admin only)"""
    current_user = get_current_user()
    
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can view admin list'}), 403
    
    admins = User.query.filter(
        (User.is_admin == True) | (User.is_deputy == True)
    ).filter_by(is_active=True).all()
    
    return jsonify({
        'admins': [user.to_dict() for user in admins],
        'count': len(admins)
    }), 200

@users_bp.route('/<int:user_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Delete user (admin only - soft delete by setting is_active=False)"""
    current_user = get_current_user()
    
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can delete users'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Cannot delete yourself
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    # Soft delete
    user.is_active = False
    db.session.commit()
    
    return jsonify({
        'message': f'User {user.username} has been deactivated',
        'user': user.to_dict()
    }), 200

@users_bp.route('/<int:user_id>/restore', methods=['PUT'])
@jwt_required()
def restore_user(user_id):
    """Restore deactivated user (admin only)"""
    current_user = get_current_user()
    
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can restore users'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.is_active:
        return jsonify({'error': 'User is already active'}), 400
    
    user.is_active = True
    db.session.commit()
    
    return jsonify({
        'message': f'User {user.username} has been restored',
        'user': user.to_dict()
    }), 200