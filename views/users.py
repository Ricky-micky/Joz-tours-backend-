from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, db

users_bp = Blueprint('users', __name__)

def is_admin_or_deputy():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user and (user.is_admin or user.is_deputy)

@users_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    users = User.query.filter_by(is_active=True).all()
    return jsonify({'users': [user.to_dict() for user in users]}), 200

@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    if current_user.id != user_id and not (current_user.is_admin or current_user.is_deputy):
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200

@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    # Only allow users to update their own profile or admins/deputies
    if current_user.id != user_id and not (current_user.is_admin or current_user.is_deputy):
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update allowed fields
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
    
    if 'profile_picture' in data:
        user.profile_picture = data['profile_picture']
    
    # Only admins can change admin/deputy status
    if current_user.is_admin:
        if 'is_deputy' in data:
            user.is_deputy = data['is_deputy']
        if 'is_active' in data:
            user.is_active = data['is_active']
    
    db.session.commit()
    
    return jsonify({
        'message': 'User updated successfully',
        'user': user.to_dict()
    }), 200

@users_bp.route('/make-deputy/<int:user_id>', methods=['PUT'])
@jwt_required()
def make_deputy(user_id):
    current_user = User.query.get(get_jwt_identity())
    
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can assign deputy roles'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.is_deputy = True
    db.session.commit()
    
    return jsonify({'message': f'User {user.username} is now a deputy admin'}), 200