from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Lodge, LodgePrice, PriceHistory, User, db
from datetime import datetime, date
from sqlalchemy import and_

prices_bp = Blueprint('prices', __name__)

def is_admin_or_deputy():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user and (user.is_admin or user.is_deputy)

@prices_bp.route('/lodges', methods=['GET'])
def get_lodges():
    lodges = Lodge.query.filter_by(is_active=True).all()
    return jsonify({
        'lodges': [{
            'id': lodge.id,
            'name': lodge.name,
            'location': lodge.location,
            'description': lodge.description,
            'rating': lodge.rating,
            'main_image': lodge.main_image
        } for lodge in lodges]
    }), 200

@prices_bp.route('/lodges/<int:lodge_id>/prices', methods=['GET'])
def get_lodge_prices(lodge_id):
    # Get current prices
    today = date.today()
    prices = LodgePrice.query.filter(
        and_(
            LodgePrice.lodge_id == lodge_id,
            LodgePrice.is_active == True,
            LodgePrice.valid_from <= today,
            LodgePrice.valid_to >= today
        )
    ).all()
    
    return jsonify({
        'prices': [{
            'id': price.id,
            'park_name': price.park_name,
            'number_of_days': price.number_of_days,
            'number_of_visitors': price.number_of_visitors,
            'price_per_person': price.price_per_person,
            'total_price': price.total_price,
            'season': price.season,
            'valid_from': price.valid_from.isoformat(),
            'valid_to': price.valid_to.isoformat()
        } for price in prices]
    }), 200

@prices_bp.route('/lodges/<int:lodge_id>/prices', methods=['POST'])
@jwt_required()
def create_lodge_price(lodge_id):
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    lodge = Lodge.query.get(lodge_id)
    if not lodge:
        return jsonify({'error': 'Lodge not found'}), 404
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['park_name', 'number_of_days', 'number_of_visitors', 
                      'price_per_person', 'valid_from', 'valid_to']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Calculate total price
    total_price = data['price_per_person'] * data['number_of_visitors'] * data['number_of_days']
    
    # Create new price
    price = LodgePrice(
        lodge_id=lodge_id,
        park_name=data['park_name'],
        number_of_days=data['number_of_days'],
        number_of_visitors=data['number_of_visitors'],
        price_per_person=data['price_per_person'],
        total_price=total_price,
        season=data.get('season', 'regular'),
        valid_from=datetime.strptime(data['valid_from'], '%Y-%m-%d').date(),
        valid_to=datetime.strptime(data['valid_to'], '%Y-%m-%d').date()
    )
    
    db.session.add(price)
    db.session.commit()
    
    return jsonify({
        'message': 'Price created successfully',
        'price': {
            'id': price.id,
            'total_price': price.total_price
        }
    }), 201

@prices_bp.route('/prices/<int:price_id>', methods=['PUT'])
@jwt_required()
def update_price(price_id):
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    price = LodgePrice.query.get(price_id)
    if not price:
        return jsonify({'error': 'Price not found'}), 404
    
    data = request.get_json()
    user_id = get_jwt_identity()
    
    # Record old price for history
    old_price = price.price_per_person
    
    # Update price
    if 'price_per_person' in data:
        price.price_per_person = data['price_per_person']
        # Recalculate total price
        price.total_price = price.price_per_person * price.number_of_visitors * price.number_of_days
        
        # Create price history record
        history = PriceHistory(
            lodge_price_id=price.id,
            old_price=old_price,
            new_price=price.price_per_person,
            edited_by_id=user_id,
            change_reason=data.get('change_reason', 'Price update')
        )
        db.session.add(history)
    
    if 'valid_from' in data:
        price.valid_from = datetime.strptime(data['valid_from'], '%Y-%m-%d').date()
    
    if 'valid_to' in data:
        price.valid_to = datetime.strptime(data['valid_to'], '%Y-%m-%d').date()
    
    if 'season' in data:
        price.season = data['season']
    
    price.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Price updated successfully',
        'price': {
            'id': price.id,
            'total_price': price.total_price,
            'updated_at': price.updated_at.isoformat()
        }
    }), 200

@prices_bp.route('/prices/<int:price_id>', methods=['DELETE'])
@jwt_required()
def delete_price(price_id):
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    price = LodgePrice.query.get(price_id)
    if not price:
        return jsonify({'error': 'Price not found'}), 404
    
    # Soft delete
    price.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'Price deleted successfully'}), 200

@prices_bp.route('/prices/<int:price_id>/history', methods=['GET'])
@jwt_required()
def get_price_history(price_id):
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    history = PriceHistory.query.filter_by(lodge_price_id=price_id)\
        .order_by(PriceHistory.created_at.desc())\
        .all()
    
    return jsonify({
        'history': [{
            'id': h.id,
            'old_price': h.old_price,
            'new_price': h.new_price,
            'change_reason': h.change_reason,
            'edited_by': h.edited_by.username,
            'created_at': h.created_at.isoformat()
        } for h in history]
    }), 200