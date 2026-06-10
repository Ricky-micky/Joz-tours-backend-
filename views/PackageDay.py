from flask import Blueprint, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from models import PackageDay
from extensions import db

# Assuming you have a db instance initialized elsewhere
# For this code to work, you need to import db from your main app

package_day_bp = Blueprint('package_days', __name__)

# CREATE - Add a new package day
@package_day_bp.route('/package-days', methods=['POST'])
def create_package_day():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['package_id', 'day_number', 'title', 'park_name']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Create new package day
        package_day = PackageDay(
            package_id=data['package_id'],
            day_number=data['day_number'],
            title=data['title'],
            description=data.get('description'),
            activities=data.get('activities', []),
            meals=data.get('meals', []),
            park_name=data['park_name'],
            park_description=data.get('park_description')
        )
        
        db.session.add(package_day)
        db.session.commit()
        
        return jsonify({
            'message': 'Package day created successfully',
            'data': package_day.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# READ - Get all package days
@package_day_bp.route('/package-days', methods=['GET'])
def get_all_package_days():
    try:
        # Get query parameters for filtering
        package_id = request.args.get('package_id')
        
        # Build query
        query = PackageDay.query
        
        if package_id:
            query = query.filter_by(package_id=int(package_id))
        
        # Order by day number
        query = query.order_by(PackageDay.day_number.asc())
        
        package_days = query.all()
        
        return jsonify({
            'count': len(package_days),
            'data': [day.to_dict() for day in package_days]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Get single package day by ID
@package_day_bp.route('/package-days/<int:day_id>', methods=['GET'])
def get_package_day(day_id):
    try:
        package_day = PackageDay.query.get_or_404(day_id)
        
        return jsonify({
            'data': package_day.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# UPDATE - Update a package day
@package_day_bp.route('/package-days/<int:day_id>', methods=['PUT'])
def update_package_day(day_id):
    try:
        package_day = PackageDay.query.get_or_404(day_id)
        data = request.get_json()
        
        # Update fields if provided
        if 'day_number' in data:
            package_day.day_number = data['day_number']
        if 'title' in data:
            package_day.title = data['title']
        if 'description' in data:
            package_day.description = data['description']
        if 'activities' in data:
            package_day.activities = data['activities']
        if 'meals' in data:
            package_day.meals = data['meals']
        if 'park_name' in data:
            package_day.park_name = data['park_name']
        if 'park_description' in data:
            package_day.park_description = data['park_description']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Package day updated successfully',
            'data': package_day.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# DELETE - Delete a package day
@package_day_bp.route('/package-days/<int:day_id>', methods=['DELETE'])
def delete_package_day(day_id):
    try:
        package_day = PackageDay.query.get_or_404(day_id)
        
        db.session.delete(package_day)
        db.session.commit()
        
        return jsonify({
            'message': 'Package day deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Bulk operations
@package_day_bp.route('/package-days/bulk', methods=['POST'])
def create_bulk_package_days():
    try:
        data = request.get_json()
        
        if not isinstance(data, list):
            return jsonify({'error': 'Request body must be an array of package days'}), 400
        
        created_days = []
        
        for day_data in data:
            # Validate required fields for each day
            required_fields = ['package_id', 'day_number', 'title', 'park_name']
            missing_fields = [field for field in required_fields if field not in day_data]
            
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields in one of the items: {", ".join(missing_fields)}'
                }), 400
            
            package_day = PackageDay(
                package_id=day_data['package_id'],
                day_number=day_data['day_number'],
                title=day_data['title'],
                description=day_data.get('description'),
                activities=day_data.get('activities', []),
                meals=day_data.get('meals', []),
                park_name=day_data['park_name'],
                park_description=day_data.get('park_description')
            )
            
            db.session.add(package_day)
            created_days.append(package_day)
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_days)} package days created successfully',
            'data': [day.to_dict() for day in created_days]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get package days by package ID
@package_day_bp.route('/packages/<int:package_id>/days', methods=['GET'])
def get_package_days_by_package(package_id):
    try:
        package_days = PackageDay.query.filter_by(package_id=package_id)\
            .order_by(PackageDay.day_number.asc())\
            .all()
        
        return jsonify({
            'package_id': package_id,
            'count': len(package_days),
            'data': [day.to_dict() for day in package_days]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500