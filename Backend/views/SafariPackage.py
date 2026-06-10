from flask import Blueprint, request, jsonify
from datetime import datetime

# Create Blueprint
safari_package_bp = Blueprint('safari_packages', __name__)

# CREATE - Add a new safari package
@safari_package_bp.route('/safari-packages', methods=['POST'])
def create_safari_package():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'total_days', 'total_nights']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Check if package name already exists
        existing_package = SafariPackage.query.filter_by(name=data['name']).first()
        if existing_package:
            return jsonify({'error': 'Package with this name already exists'}), 409
        
        # Create new safari package
        safari_package = SafariPackage(
            name=data['name'],
            description=data.get('description', ''),
            total_days=data['total_days'],
            total_nights=data['total_nights'],
            is_active=data.get('is_active', True)
        )
        
        db.session.add(safari_package)
        db.session.commit()
        
        return jsonify({
            'message': 'Safari package created successfully',
            'data': safari_package.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# READ - Get all safari packages
@safari_package_bp.route('/safari-packages', methods=['GET'])
def get_all_safari_packages():
    try:
        # Get query parameters for filtering
        is_active = request.args.get('is_active')
        name = request.args.get('name')
        
        # Build query
        query = SafariPackage.query
        
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']
            query = query.filter_by(is_active=is_active_bool)
        
        if name:
            query = query.filter(SafariPackage.name.ilike(f'%{name}%'))
        
        # Order by creation date (newest first)
        query = query.order_by(SafariPackage.created_at.desc())
        
        safari_packages = query.all()
        
        return jsonify({
            'count': len(safari_packages),
            'data': [package.to_dict() for package in safari_packages]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Get single safari package by ID
@safari_package_bp.route('/safari-packages/<int:package_id>', methods=['GET'])
def get_safari_package(package_id):
    try:
        safari_package = SafariPackage.query.get_or_404(package_id)
        
        return jsonify({
            'data': safari_package.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# UPDATE - Update a safari package
@safari_package_bp.route('/safari-packages/<int:package_id>', methods=['PUT'])
def update_safari_package(package_id):
    try:
        safari_package = SafariPackage.query.get_or_404(package_id)
        data = request.get_json()
        
        # Check if updating name would cause conflict
        if 'name' in data and data['name'] != safari_package.name:
            existing_package = SafariPackage.query.filter_by(name=data['name']).first()
            if existing_package:
                return jsonify({'error': 'Package with this name already exists'}), 409
        
        # Update fields if provided
        if 'name' in data:
            safari_package.name = data['name']
        if 'description' in data:
            safari_package.description = data['description']
        if 'total_days' in data:
            safari_package.total_days = data['total_days']
        if 'total_nights' in data:
            safari_package.total_nights = data['total_nights']
        if 'is_active' in data:
            safari_package.is_active = data['is_active']
        
        safari_package.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Safari package updated successfully',
            'data': safari_package.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# DELETE - Delete a safari package
@safari_package_bp.route('/safari-packages/<int:package_id>', methods=['DELETE'])
def delete_safari_package(package_id):
    try:
        safari_package = SafariPackage.query.get_or_404(package_id)
        
        db.session.delete(safari_package)
        db.session.commit()
        
        return jsonify({
            'message': 'Safari package deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Additional routes
@safari_package_bp.route('/safari-packages/search', methods=['GET'])
def search_safari_packages():
    try:
        search_term = request.args.get('q', '')
        
        query = SafariPackage.query
        
        if search_term:
            query = query.filter(
                (SafariPackage.name.ilike(f'%{search_term}%')) |
                (SafariPackage.description.ilike(f'%{search_term}%'))
            )
        
        query = query.filter_by(is_active=True).order_by(SafariPackage.name)
        safari_packages = query.all()
        
        return jsonify({
            'count': len(safari_packages),
            'data': [package.to_dict() for package in safari_packages]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@safari_package_bp.route('/safari-packages/<int:package_id>/toggle', methods=['PATCH'])
def toggle_package_active(package_id):
    try:
        safari_package = SafariPackage.query.get_or_404(package_id)
        
        safari_package.is_active = not safari_package.is_active
        safari_package.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        status = "activated" if safari_package.is_active else "deactivated"
        
        return jsonify({
            'message': f'Safari package {status} successfully',
            'data': safari_package.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500