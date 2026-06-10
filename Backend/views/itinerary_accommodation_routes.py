from flask import Blueprint, request, jsonify
from datetime import datetime
from models import ItineraryAccommodation, PackageItinerary
from extensions import db
# Create Blueprint
itinerary_accommodation_bp = Blueprint('itinerary_accommodations', __name__)

# CREATE - Add a new itinerary accommodation
@itinerary_accommodation_bp.route('/itinerary-accommodations', methods=['POST'])
def create_itinerary_accommodation():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['itinerary_id', 'day_number', 'accommodation_name']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Check if accommodation already exists for this day in the itinerary
        existing_accommodation = ItineraryAccommodation.query.filter_by(
            itinerary_id=data['itinerary_id'],
            day_number=data['day_number']
        ).first()
        
        if existing_accommodation:
            return jsonify({
                'error': f'Accommodation already exists for day {data["day_number"]} in this itinerary'
            }), 409
        
        # Create new itinerary accommodation
        itinerary_accommodation = ItineraryAccommodation(
            itinerary_id=data['itinerary_id'],
            day_number=data['day_number'],
            accommodation_name=data['accommodation_name']
        )
        
        db.session.add(itinerary_accommodation)
        db.session.commit()
        
        return jsonify({
            'message': 'Itinerary accommodation created successfully',
            'data': itinerary_accommodation.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# READ - Get all itinerary accommodations
@itinerary_accommodation_bp.route('/itinerary-accommodations', methods=['GET'])
def get_all_itinerary_accommodations():
    try:
        # Get query parameters for filtering
        itinerary_id = request.args.get('itinerary_id')
        day_number = request.args.get('day_number')
        
        # Build query
        query = ItineraryAccommodation.query
        
        if itinerary_id:
            query = query.filter_by(itinerary_id=int(itinerary_id))
        
        if day_number:
            query = query.filter_by(day_number=int(day_number))
        
        # Order by day number
        query = query.order_by(ItineraryAccommodation.day_number.asc())
        
        itinerary_accommodations = query.all()
        
        return jsonify({
            'count': len(itinerary_accommodations),
            'data': [accommodation.to_dict() for accommodation in itinerary_accommodations]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Get single itinerary accommodation by ID
@itinerary_accommodation_bp.route('/itinerary-accommodations/<int:accommodation_id>', methods=['GET'])
def get_itinerary_accommodation(accommodation_id):
    try:
        itinerary_accommodation = ItineraryAccommodation.query.get_or_404(accommodation_id)
        
        return jsonify({
            'data': itinerary_accommodation.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# UPDATE - Update an itinerary accommodation
@itinerary_accommodation_bp.route('/itinerary-accommodations/<int:accommodation_id>', methods=['PUT'])
def update_itinerary_accommodation(accommodation_id):
    try:
        itinerary_accommodation = ItineraryAccommodation.query.get_or_404(accommodation_id)
        data = request.get_json()
        
        # Check if updating day number would cause conflict
        if 'day_number' in data and data['day_number'] != itinerary_accommodation.day_number:
            existing_accommodation = ItineraryAccommodation.query.filter_by(
                itinerary_id=itinerary_accommodation.itinerary_id,
                day_number=data['day_number']
            ).first()
            
            if existing_accommodation and existing_accommodation.id != accommodation_id:
                return jsonify({
                    'error': f'Accommodation already exists for day {data["day_number"]} in this itinerary'
                }), 409
        
        # Update fields if provided
        if 'day_number' in data:
            itinerary_accommodation.day_number = data['day_number']
        if 'accommodation_name' in data:
            itinerary_accommodation.accommodation_name = data['accommodation_name']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Itinerary accommodation updated successfully',
            'data': itinerary_accommodation.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# DELETE - Delete an itinerary accommodation
@itinerary_accommodation_bp.route('/itinerary-accommodations/<int:accommodation_id>', methods=['DELETE'])
def delete_itinerary_accommodation(accommodation_id):
    try:
        itinerary_accommodation = ItineraryAccommodation.query.get_or_404(accommodation_id)
        
        db.session.delete(itinerary_accommodation)
        db.session.commit()
        
        return jsonify({
            'message': 'Itinerary accommodation deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get accommodations for a specific itinerary
@itinerary_accommodation_bp.route('/itineraries/<int:itinerary_id>/accommodations', methods=['GET'])
def get_itinerary_accommodations(itinerary_id):
    try:
        # Verify itinerary exists
        itinerary = PackageItinerary.query.get_or_404(itinerary_id)
        
        accommodations = ItineraryAccommodation.query.filter_by(itinerary_id=itinerary_id)\
            .order_by(ItineraryAccommodation.day_number.asc())\
            .all()
        
        return jsonify({
            'itinerary_id': itinerary_id,
            'itinerary_name': itinerary.name,
            'count': len(accommodations),
            'data': [acc.to_dict() for acc in accommodations]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get accommodation for a specific day in an itinerary
@itinerary_accommodation_bp.route('/itineraries/<int:itinerary_id>/day/<int:day_number>/accommodation', methods=['GET'])
def get_accommodation_for_day(itinerary_id, day_number):
    try:
        accommodation = ItineraryAccommodation.query.filter_by(
            itinerary_id=itinerary_id,
            day_number=day_number
        ).first()
        
        if not accommodation:
            return jsonify({
                'message': f'No accommodation found for day {day_number} in itinerary {itinerary_id}',
                'data': None
            }), 404
        
        return jsonify({
            'data': accommodation.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Bulk create itinerary accommodations
@itinerary_accommodation_bp.route('/itinerary-accommodations/bulk', methods=['POST'])
def create_bulk_itinerary_accommodations():
    try:
        data = request.get_json()
        
        if 'itinerary_id' not in data:
            return jsonify({'error': 'itinerary_id is required'}), 400
        
        if 'accommodations' not in data or not isinstance(data['accommodations'], list):
            return jsonify({'error': 'accommodations array is required'}), 400
        
        itinerary_id = data['itinerary_id']
        accommodations_data = data['accommodations']
        
        created_accommodations = []
        
        for acc_data in accommodations_data:
            # Validate required fields for each accommodation
            required_fields = ['day_number', 'accommodation_name']
            missing_fields = [field for field in required_fields if field not in acc_data]
            
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields in one of the items: {", ".join(missing_fields)}'
                }), 400
            
            # Check if accommodation already exists for this day
            existing_accommodation = ItineraryAccommodation.query.filter_by(
                itinerary_id=itinerary_id,
                day_number=acc_data['day_number']
            ).first()
            
            if not existing_accommodation:
                itinerary_accommodation = ItineraryAccommodation(
                    itinerary_id=itinerary_id,
                    day_number=acc_data['day_number'],
                    accommodation_name=acc_data['accommodation_name']
                )
                
                db.session.add(itinerary_accommodation)
                created_accommodations.append(itinerary_accommodation)
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_accommodations)} itinerary accommodations created successfully',
            'data': [acc.to_dict() for acc in created_accommodations]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Update multiple accommodations (replace all for an itinerary)
@itinerary_accommodation_bp.route('/itineraries/<int:itinerary_id>/accommodations/replace', methods=['PUT'])
def replace_itinerary_accommodations(itinerary_id):
    try:
        data = request.get_json()
        
        if 'accommodations' not in data or not isinstance(data['accommodations'], list):
            return jsonify({'error': 'accommodations array is required'}), 400
        
        # Verify itinerary exists
        itinerary = PackageItinerary.query.get_or_404(itinerary_id)
        
        # Delete existing accommodations for this itinerary
        ItineraryAccommodation.query.filter_by(itinerary_id=itinerary_id).delete()
        
        # Create new accommodations
        created_accommodations = []
        
        for acc_data in data['accommodations']:
            # Validate required fields for each accommodation
            required_fields = ['day_number', 'accommodation_name']
            missing_fields = [field for field in required_fields if field not in acc_data]
            
            if missing_fields:
                db.session.rollback()
                return jsonify({
                    'error': f'Missing required fields in one of the items: {", ".join(missing_fields)}'
                }), 400
            
            itinerary_accommodation = ItineraryAccommodation(
                itinerary_id=itinerary_id,
                day_number=acc_data['day_number'],
                accommodation_name=acc_data['accommodation_name']
            )
            
            db.session.add(itinerary_accommodation)
            created_accommodations.append(itinerary_accommodation)
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_accommodations)} itinerary accommodations replaced successfully',
            'data': [acc.to_dict() for acc in created_accommodations]
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Search accommodations by name
@itinerary_accommodation_bp.route('/itinerary-accommodations/search', methods=['GET'])
def search_itinerary_accommodations():
    try:
        search_term = request.args.get('q', '')
        itinerary_id = request.args.get('itinerary_id')
        
        query = ItineraryAccommodation.query
        
        if search_term:
            query = query.filter(ItineraryAccommodation.accommodation_name.ilike(f'%{search_term}%'))
        
        if itinerary_id:
            query = query.filter_by(itinerary_id=int(itinerary_id))
        
        query = query.order_by(ItineraryAccommodation.day_number.asc())
        accommodations = query.all()
        
        return jsonify({
            'count': len(accommodations),
            'search_term': search_term,
            'data': [acc.to_dict() for acc in accommodations]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get accommodations grouped by day
@itinerary_accommodation_bp.route('/itineraries/<int:itinerary_id>/accommodations/grouped', methods=['GET'])
def get_grouped_accommodations(itinerary_id):
    try:
        # Verify itinerary exists
        itinerary = PackageItinerary.query.get_or_404(itinerary_id)
        
        accommodations = ItineraryAccommodation.query.filter_by(itinerary_id=itinerary_id)\
            .order_by(ItineraryAccommodation.day_number.asc())\
            .all()
        
        # Group accommodations by day
        grouped_data = {}
        for acc in accommodations:
            day_key = f"Day {acc.day_number}"
            if day_key not in grouped_data:
                grouped_data[day_key] = []
            grouped_data[day_key].append(acc.to_dict())
        
        return jsonify({
            'itinerary_id': itinerary_id,
            'itinerary_name': itinerary.name,
            'count': len(accommodations),
            'grouped_data': grouped_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500