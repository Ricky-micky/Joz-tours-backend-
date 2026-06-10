from flask import Blueprint, request, jsonify
from datetime import datetime
from models import PackageItinerary
from extensions import db
# Create Blueprint
package_itinerary_bp = Blueprint('package_itineraries', __name__)

# CREATE - Add a new package itinerary
@package_itinerary_bp.route('/package-itineraries', methods=['POST'])
def create_package_itinerary():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['package_id', 'itinerary_code', 'name']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Check if itinerary code already exists for this package
        existing_itinerary = PackageItinerary.query.filter_by(
            package_id=data['package_id'],
            itinerary_code=data['itinerary_code']
        ).first()
        
        if existing_itinerary:
            return jsonify({'error': 'Itinerary code already exists for this package'}), 409
        
        # If setting as default, unset any existing default for this package
        if data.get('is_default', False):
            PackageItinerary.query.filter_by(
                package_id=data['package_id'],
                is_default=True
            ).update({'is_default': False})
        
        # Create new package itinerary
        package_itinerary = PackageItinerary(
            package_id=data['package_id'],
            itinerary_code=data['itinerary_code'],
            name=data['name'],
            description=data.get('description'),
            is_default=data.get('is_default', False)
        )
        
        db.session.add(package_itinerary)
        db.session.commit()
        
        return jsonify({
            'message': 'Package itinerary created successfully',
            'data': package_itinerary.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# READ - Get all package itineraries
@package_itinerary_bp.route('/package-itineraries', methods=['GET'])
def get_all_package_itineraries():
    try:
        # Get query parameters for filtering
        package_id = request.args.get('package_id')
        itinerary_code = request.args.get('itinerary_code')
        is_default = request.args.get('is_default')
        
        # Build query
        query = PackageItinerary.query
        
        if package_id:
            query = query.filter_by(package_id=int(package_id))
        
        if itinerary_code:
            query = query.filter_by(itinerary_code=itinerary_code)
        
        if is_default is not None:
            is_default_bool = is_default.lower() in ['true', '1', 'yes']
            query = query.filter_by(is_default=is_default_bool)
        
        # Order by name
        query = query.order_by(PackageItinerary.name)
        
        package_itineraries = query.all()
        
        return jsonify({
            'count': len(package_itineraries),
            'data': [itinerary.to_dict() for itinerary in package_itineraries]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Get single package itinerary by ID
@package_itinerary_bp.route('/package-itineraries/<int:itinerary_id>', methods=['GET'])
def get_package_itinerary(itinerary_id):
    try:
        package_itinerary = PackageItinerary.query.get_or_404(itinerary_id)
        
        return jsonify({
            'data': package_itinerary.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# UPDATE - Update a package itinerary
@package_itinerary_bp.route('/package-itineraries/<int:itinerary_id>', methods=['PUT'])
def update_package_itinerary(itinerary_id):
    try:
        package_itinerary = PackageItinerary.query.get_or_404(itinerary_id)
        data = request.get_json()
        
        # Check if updating itinerary code would cause conflict
        if 'itinerary_code' in data and data['itinerary_code'] != package_itinerary.itinerary_code:
            existing_itinerary = PackageItinerary.query.filter_by(
                package_id=package_itinerary.package_id,
                itinerary_code=data['itinerary_code']
            ).first()
            
            if existing_itinerary:
                return jsonify({'error': 'Itinerary code already exists for this package'}), 409
        
        # If setting as default, unset any existing default for this package
        if 'is_default' in data and data['is_default'] and not package_itinerary.is_default:
            PackageItinerary.query.filter_by(
                package_id=package_itinerary.package_id,
                is_default=True
            ).update({'is_default': False})
        
        # Update fields if provided
        if 'itinerary_code' in data:
            package_itinerary.itinerary_code = data['itinerary_code']
        if 'name' in data:
            package_itinerary.name = data['name']
        if 'description' in data:
            package_itinerary.description = data['description']
        if 'is_default' in data:
            package_itinerary.is_default = data['is_default']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Package itinerary updated successfully',
            'data': package_itinerary.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# DELETE - Delete a package itinerary
@package_itinerary_bp.route('/package-itineraries/<int:itinerary_id>', methods=['DELETE'])
def delete_package_itinerary(itinerary_id):
    try:
        package_itinerary = PackageItinerary.query.get_or_404(itinerary_id)
        
        # Check if this is the default itinerary
        if package_itinerary.is_default:
            return jsonify({'error': 'Cannot delete default itinerary. Set another itinerary as default first.'}), 400
        
        db.session.delete(package_itinerary)
        db.session.commit()
        
        return jsonify({
            'message': 'Package itinerary deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get default itinerary for a package
@package_itinerary_bp.route('/packages/<int:package_id>/default-itinerary', methods=['GET'])
def get_default_itinerary(package_id):
    try:
        default_itinerary = PackageItinerary.query.filter_by(
            package_id=package_id,
            is_default=True
        ).first()
        
        if not default_itinerary:
            return jsonify({
                'message': 'No default itinerary found for this package',
                'data': None
            })
        
        return jsonify({
            'data': default_itinerary.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Set an itinerary as default
@package_itinerary_bp.route('/package-itineraries/<int:itinerary_id>/set-default', methods=['PATCH'])
def set_default_itinerary(itinerary_id):
    try:
        package_itinerary = PackageItinerary.query.get_or_404(itinerary_id)
        
        # Unset any existing default for this package
        PackageItinerary.query.filter_by(
            package_id=package_itinerary.package_id,
            is_default=True
        ).update({'is_default': False})
        
        # Set this itinerary as default
        package_itinerary.is_default = True
        
        db.session.commit()
        
        return jsonify({
            'message': 'Itinerary set as default successfully',
            'data': package_itinerary.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get all itineraries for a specific package
@package_itinerary_bp.route('/packages/<int:package_id>/itineraries', methods=['GET'])
def get_package_itineraries(package_id):
    try:
        package_itineraries = PackageItinerary.query.filter_by(package_id=package_id)\
            .order_by(PackageItinerary.name)\
            .all()
        
        return jsonify({
            'package_id': package_id,
            'count': len(package_itineraries),
            'data': [itinerary.to_dict() for itinerary in package_itineraries]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Bulk create package itineraries
@package_itinerary_bp.route('/package-itineraries/bulk', methods=['POST'])
def create_bulk_package_itineraries():
    try:
        data = request.get_json()
        
        if not isinstance(data, list):
            return jsonify({'error': 'Request body must be an array of package itineraries'}), 400
        
        created_itineraries = []
        
        for itinerary_data in data:
            # Validate required fields for each itinerary
            required_fields = ['package_id', 'itinerary_code', 'name']
            missing_fields = [field for field in required_fields if field not in itinerary_data]
            
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields in one of the items: {", ".join(missing_fields)}'
                }), 400
            
            # Check if itinerary code already exists for this package
            existing_itinerary = PackageItinerary.query.filter_by(
                package_id=itinerary_data['package_id'],
                itinerary_code=itinerary_data['itinerary_code']
            ).first()
            
            if existing_itinerary:
                continue  # Skip duplicates
            
            package_itinerary = PackageItinerary(
                package_id=itinerary_data['package_id'],
                itinerary_code=itinerary_data['itinerary_code'],
                name=itinerary_data['name'],
                description=itinerary_data.get('description'),
                is_default=itinerary_data.get('is_default', False)
            )
            
            db.session.add(package_itinerary)
            created_itineraries.append(package_itinerary)
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_itineraries)} package itineraries created successfully',
            'data': [itinerary.to_dict() for itinerary in created_itineraries]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get itinerary with all accommodations
@package_itinerary_bp.route('/package-itineraries/<int:itinerary_id>/with-accommodations', methods=['GET'])
def get_itinerary_with_accommodations(itinerary_id):
    try:
        package_itinerary = PackageItinerary.query.get_or_404(itinerary_id)
        
        # Ensure accommodations are loaded
        itinerary_data = package_itinerary.to_dict()
        
        return jsonify({
            'data': itinerary_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404