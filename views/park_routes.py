from flask import Blueprint, request, jsonify
from datetime import datetime   
from models import Park
from extensions import db


# Create Blueprint
park_bp = Blueprint('parks', __name__)

# CREATE - Add a new park
@park_bp.route('/parks', methods=['POST'])
def create_park():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Check if park name already exists
        existing_park = Park.query.filter_by(name=data['name']).first()
        if existing_park:
            return jsonify({'error': 'Park with this name already exists'}), 409
        
        # Create new park
        park = Park(
            name=data['name'],
            location=data.get('location'),
            description=data.get('description'),
            known_for=data.get('known_for', []),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(park)
        db.session.commit()
        
        return jsonify({
            'message': 'Park created successfully',
            'data': park.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# READ - Get all parks
@park_bp.route('/parks', methods=['GET'])
def get_all_parks():
    try:
        # Get query parameters for filtering
        is_active = request.args.get('is_active')
        name = request.args.get('name')
        location = request.args.get('location')
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        query = Park.query
        
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']
            query = query.filter_by(is_active=is_active_bool)
        
        if name:
            query = query.filter(Park.name.ilike(f'%{name}%'))
        
        if location:
            query = query.filter(Park.location.ilike(f'%{location}%'))
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply ordering and pagination
        query = query.order_by(Park.name.asc())
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        parks = query.all()
        
        return jsonify({
            'count': len(parks),
            'total': total_count,
            'offset': offset,
            'limit': limit if limit else 'none',
            'data': [park.to_dict() for park in parks]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Get single park by ID
@park_bp.route('/parks/<int:park_id>', methods=['GET'])
def get_park(park_id):
    try:
        park = Park.query.get_or_404(park_id)
        
        return jsonify({
            'data': park.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# UPDATE - Update a park
@park_bp.route('/parks/<int:park_id>', methods=['PUT'])
def update_park(park_id):
    try:
        park = Park.query.get_or_404(park_id)
        data = request.get_json()
        
        # Check if updating name would cause conflict
        if 'name' in data and data['name'] != park.name:
            existing_park = Park.query.filter_by(name=data['name']).first()
            if existing_park:
                return jsonify({'error': 'Park with this name already exists'}), 409
        
        # Update fields if provided
        if 'name' in data:
            park.name = data['name']
        if 'location' in data:
            park.location = data['location']
        if 'description' in data:
            park.description = data['description']
        if 'known_for' in data:
            park.known_for = data['known_for']
        if 'is_active' in data:
            park.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Park updated successfully',
            'data': park.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# DELETE - Delete a park
@park_bp.route('/parks/<int:park_id>', methods=['DELETE'])
def delete_park(park_id):
    try:
        park = Park.query.get_or_404(park_id)
        
        db.session.delete(park)
        db.session.commit()
        
        return jsonify({
            'message': 'Park deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Toggle park active status
@park_bp.route('/parks/<int:park_id>/toggle-active', methods=['PATCH'])
def toggle_park_active(park_id):
    try:
        park = Park.query.get_or_404(park_id)
        
        park.is_active = not park.is_active
        
        db.session.commit()
        
        status = "activated" if park.is_active else "deactivated"
        
        return jsonify({
            'message': f'Park {status} successfully',
            'data': park.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Search parks by name or location
@park_bp.route('/parks/search', methods=['GET'])
def search_parks():
    try:
        search_term = request.args.get('q', '')
        is_active = request.args.get('is_active', 'true')
        
        if not search_term:
            return jsonify({'error': 'Search term is required'}), 400
        
        query = Park.query
        
        query = query.filter(
            (Park.name.ilike(f'%{search_term}%')) |
            (Park.location.ilike(f'%{search_term}%')) |
            (Park.description.ilike(f'%{search_term}%'))
        )
        
        if is_active.lower() in ['true', '1', 'yes']:
            query = query.filter_by(is_active=True)
        
        query = query.order_by(Park.name)
        parks = query.all()
        
        return jsonify({
            'count': len(parks),
            'search_term': search_term,
            'data': [park.to_dict() for park in parks]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get active parks only
@park_bp.route('/parks/active', methods=['GET'])
def get_active_parks():
    try:
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = Park.query.filter_by(is_active=True)\
                          .order_by(Park.name.asc())
        
        # Get total count before pagination
        total_count = query.count()
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        parks = query.all()
        
        return jsonify({
            'count': len(parks),
            'total': total_count,
            'data': [park.to_dict() for park in parks]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Bulk create parks
@park_bp.route('/parks/bulk', methods=['POST'])
def create_bulk_parks():
    try:
        data = request.get_json()
        
        if not isinstance(data, list):
            return jsonify({'error': 'Request body must be an array of parks'}), 400
        
        created_parks = []
        
        for park_data in data:
            # Validate required fields for each park
            required_fields = ['name']
            missing_fields = [field for field in required_fields if field not in park_data]
            
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields in one of the items: {", ".join(missing_fields)}'
                }), 400
            
            # Check if park name already exists
            existing_park = Park.query.filter_by(name=park_data['name']).first()
            if existing_park:
                continue  # Skip duplicates
            
            park = Park(
                name=park_data['name'],
                location=park_data.get('location'),
                description=park_data.get('description'),
                known_for=park_data.get('known_for', []),
                is_active=park_data.get('is_active', True)
            )
            
            db.session.add(park)
            created_parks.append(park)
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_parks)} parks created successfully',
            'data': [park.to_dict() for park in created_parks]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get park by name
@park_bp.route('/parks/name/<string:park_name>', methods=['GET'])
def get_park_by_name(park_name):
    try:
        park = Park.query.filter_by(name=park_name).first()
        
        if not park:
            return jsonify({
                'message': f'Park "{park_name}" not found',
                'data': None
            }), 404
        
        return jsonify({
            'data': park.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get parks grouped by location
@park_bp.route('/parks/grouped-by-location', methods=['GET'])
def get_parks_grouped_by_location():
    try:
        is_active = request.args.get('is_active', 'true')
        
        query = Park.query
        
        if is_active.lower() in ['true', '1', 'yes']:
            query = query.filter_by(is_active=True)
        
        parks = query.order_by(Park.location.asc(), Park.name.asc()).all()
        
        # Group parks by location
        grouped_parks = {}
        for park in parks:
            location = park.location or 'Unknown Location'
            if location not in grouped_parks:
                grouped_parks[location] = []
            grouped_parks[location].append(park.to_dict())
        
        return jsonify({
            'count': len(parks),
            'locations_count': len(grouped_parks),
            'data': grouped_parks
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get parks with specific features (known_for)
@park_bp.route('/parks/with-feature', methods=['GET'])
def get_parks_with_feature():
    try:
        feature = request.args.get('feature', '')
        
        if not feature:
            return jsonify({'error': 'Feature parameter is required'}), 400
        
        # Get all parks and filter by feature
        parks = Park.query.filter_by(is_active=True).all()
        
        filtered_parks = []
        for park in parks:
            if park.known_for and feature.lower() in [f.lower() for f in park.known_for]:
                filtered_parks.append(park.to_dict())
        
        return jsonify({
            'count': len(filtered_parks),
            'feature': feature,
            'data': filtered_parks
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get park statistics
@park_bp.route('/parks/stats', methods=['GET'])
def get_park_stats():
    try:
        # Get counts
        total_parks = Park.query.count()
        active_parks = Park.query.filter_by(is_active=True).count()
        inactive_parks = total_parks - active_parks
        
        # Get parks with locations
        parks_with_location = Park.query.filter(Park.location.isnot(None)).count()
        
        # Get unique locations
        unique_locations = db.session.query(Park.location)\
            .filter(Park.location.isnot(None))\
            .distinct()\
            .count()
        
        stats = {
            'total_parks': total_parks,
            'active_parks': active_parks,
            'inactive_parks': inactive_parks,
            'parks_with_location': parks_with_location,
            'unique_locations': unique_locations,
            'percentage_with_location': round((parks_with_location / total_parks * 100) if total_parks > 0 else 0, 2)
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update known_for for a park
@park_bp.route('/parks/<int:park_id>/known-for', methods=['PUT'])
def update_park_known_for(park_id):
    try:
        park = Park.query.get_or_404(park_id)
        data = request.get_json()
        
        if 'known_for' not in data:
            return jsonify({'error': 'known_for field is required'}), 400
        
        if not isinstance(data['known_for'], list):
            return jsonify({'error': 'known_for must be an array'}), 400
        
        park.known_for = data['known_for']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Park features updated successfully',
            'data': park.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Add feature to park's known_for
@park_bp.route('/parks/<int:park_id>/add-feature', methods=['PATCH'])
def add_park_feature(park_id):
    try:
        park = Park.query.get_or_404(park_id)
        data = request.get_json()
        
        if 'feature' not in data:
            return jsonify({'error': 'feature field is required'}), 400
        
        feature = data['feature'].strip()
        if not feature:
            return jsonify({'error': 'feature cannot be empty'}), 400
        
        # Initialize known_for if None
        if park.known_for is None:
            park.known_for = []
        
        # Add feature if not already present
        if feature not in park.known_for:
            park.known_for.append(feature)
        
        db.session.commit()
        
        return jsonify({
            'message': f'Feature "{feature}" added successfully',
            'data': park.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Remove feature from park's known_for
@park_bp.route('/parks/<int:park_id>/remove-feature', methods=['PATCH'])
def remove_park_feature(park_id):
    try:
        park = Park.query.get_or_404(park_id)
        data = request.get_json()
        
        if 'feature' not in data:
            return jsonify({'error': 'feature field is required'}), 400
        
        feature = data['feature']
        
        # Check if feature exists
        if park.known_for and feature in park.known_for:
            park.known_for.remove(feature)
        else:
            return jsonify({'error': f'Feature "{feature}" not found'}), 404
        
        db.session.commit()
        
        return jsonify({
            'message': f'Feature "{feature}" removed successfully',
            'data': park.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500