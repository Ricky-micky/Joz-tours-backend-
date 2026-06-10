from flask import Blueprint, request, jsonify
from datetime import datetime, date
from models import PackagePrice
from extensions import db


# Create Blueprint
package_price_bp = Blueprint('package_prices', __name__)

# CREATE - Add a new package price
@package_price_bp.route('/package-prices', methods=['POST'])
def create_package_price():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = [
            'package_id', 'itinerary_id', 
            'pax_2_price', 'pax_4_price', 'pax_6_price', 'pax_8_price',
            'valid_from', 'valid_to'
        ]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Convert date strings to date objects
        try:
            valid_from = datetime.strptime(data['valid_from'], '%Y-%m-%d').date()
            valid_to = datetime.strptime(data['valid_to'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Validate date range
        if valid_from >= valid_to:
            return jsonify({'error': 'valid_from must be before valid_to'}), 400
        
        # Check for overlapping price periods for the same package and itinerary
        overlapping_price = PackagePrice.query.filter(
            PackagePrice.package_id == data['package_id'],
            PackagePrice.itinerary_id == data['itinerary_id'],
            PackagePrice.valid_from <= valid_to,
            PackagePrice.valid_to >= valid_from
        ).first()
        
        if overlapping_price:
            return jsonify({
                'error': 'Price period overlaps with existing price for this package and itinerary'
            }), 409
        
        # Create new package price
        package_price = PackagePrice(
            package_id=data['package_id'],
            itinerary_id=data['itinerary_id'],
            pax_2_price=data['pax_2_price'],
            pax_4_price=data['pax_4_price'],
            pax_6_price=data['pax_6_price'],
            pax_8_price=data['pax_8_price'],
            single_supplement=data.get('single_supplement'),
            child_price=data.get('child_price'),
            includes=data.get('includes', []),
            excludes=data.get('excludes', []),
            valid_from=valid_from,
            valid_to=valid_to,
            is_active=data.get('is_active', True)
        )
        
        db.session.add(package_price)
        db.session.commit()
        
        return jsonify({
            'message': 'Package price created successfully',
            'data': package_price.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# READ - Get all package prices
@package_price_bp.route('/package-prices', methods=['GET'])
def get_all_package_prices():
    try:
        # Get query parameters for filtering
        package_id = request.args.get('package_id')
        itinerary_id = request.args.get('itinerary_id')
        is_active = request.args.get('is_active')
        date_filter = request.args.get('date')
        
        # Build query
        query = PackagePrice.query
        
        if package_id:
            query = query.filter_by(package_id=int(package_id))
        
        if itinerary_id:
            query = query.filter_by(itinerary_id=int(itinerary_id))
        
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']
            query = query.filter_by(is_active=is_active_bool)
        
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                query = query.filter(
                    PackagePrice.valid_from <= filter_date,
                    PackagePrice.valid_to >= filter_date
                )
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Order by validity period
        query = query.order_by(PackagePrice.valid_from.desc())
        
        package_prices = query.all()
        
        return jsonify({
            'count': len(package_prices),
            'data': [price.to_dict() for price in package_prices]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Get single package price by ID
@package_price_bp.route('/package-prices/<int:price_id>', methods=['GET'])
def get_package_price(price_id):
    try:
        package_price = PackagePrice.query.get_or_404(price_id)
        
        return jsonify({
            'data': package_price.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# UPDATE - Update a package price
@package_price_bp.route('/package-prices/<int:price_id>', methods=['PUT'])
def update_package_price(price_id):
    try:
        package_price = PackagePrice.query.get_or_404(price_id)
        data = request.get_json()
        
        # Handle date updates
        valid_from = package_price.valid_from
        valid_to = package_price.valid_to
        
        if 'valid_from' in data:
            try:
                valid_from = datetime.strptime(data['valid_from'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid valid_from date format. Use YYYY-MM-DD'}), 400
        
        if 'valid_to' in data:
            try:
                valid_to = datetime.strptime(data['valid_to'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid valid_to date format. Use YYYY-MM-DD'}), 400
        
        # Validate date range
        if valid_from >= valid_to:
            return jsonify({'error': 'valid_from must be before valid_to'}), 400
        
        # Check for overlapping price periods (excluding current price)
        if 'valid_from' in data or 'valid_to' in data:
            overlapping_price = PackagePrice.query.filter(
                PackagePrice.package_id == package_price.package_id,
                PackagePrice.itinerary_id == package_price.itinerary_id,
                PackagePrice.id != price_id,
                PackagePrice.valid_from <= valid_to,
                PackagePrice.valid_to >= valid_from
            ).first()
            
            if overlapping_price:
                return jsonify({
                    'error': 'Price period overlaps with existing price for this package and itinerary'
                }), 409
        
        # Update fields if provided
        if 'pax_2_price' in data:
            package_price.pax_2_price = data['pax_2_price']
        if 'pax_4_price' in data:
            package_price.pax_4_price = data['pax_4_price']
        if 'pax_6_price' in data:
            package_price.pax_6_price = data['pax_6_price']
        if 'pax_8_price' in data:
            package_price.pax_8_price = data['pax_8_price']
        if 'single_supplement' in data:
            package_price.single_supplement = data['single_supplement']
        if 'child_price' in data:
            package_price.child_price = data['child_price']
        if 'includes' in data:
            package_price.includes = data['includes']
        if 'excludes' in data:
            package_price.excludes = data['excludes']
        if 'valid_from' in data:
            package_price.valid_from = valid_from
        if 'valid_to' in data:
            package_price.valid_to = valid_to
        if 'is_active' in data:
            package_price.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Package price updated successfully',
            'data': package_price.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# DELETE - Delete a package price
@package_price_bp.route('/package-prices/<int:price_id>', methods=['DELETE'])
def delete_package_price(price_id):
    try:
        package_price = PackagePrice.query.get_or_404(price_id)
        
        db.session.delete(package_price)
        db.session.commit()
        
        return jsonify({
            'message': 'Package price deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get current active price for a package and itinerary
@package_price_bp.route('/packages/<int:package_id>/itineraries/<int:itinerary_id>/current-price', methods=['GET'])
def get_current_price(package_id, itinerary_id):
    try:
        today = date.today()
        
        current_price = PackagePrice.query.filter(
            PackagePrice.package_id == package_id,
            PackagePrice.itinerary_id == itinerary_id,
            PackagePrice.valid_from <= today,
            PackagePrice.valid_to >= today,
            PackagePrice.is_active == True
        ).order_by(PackagePrice.created_at.desc()).first()
        
        if not current_price:
            return jsonify({
                'message': 'No active price found for the current date',
                'data': None
            }), 404
        
        return jsonify({
            'data': current_price.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get all prices for a specific package
@package_price_bp.route('/packages/<int:package_id>/prices', methods=['GET'])
def get_package_prices(package_id):
    try:
        is_active = request.args.get('is_active', 'true')
        
        query = PackagePrice.query.filter_by(package_id=package_id)
        
        if is_active.lower() in ['true', '1', 'yes']:
            query = query.filter_by(is_active=True)
        
        query = query.order_by(PackagePrice.valid_from.desc())
        package_prices = query.all()
        
        return jsonify({
            'package_id': package_id,
            'count': len(package_prices),
            'data': [price.to_dict() for price in package_prices]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get all prices for a specific itinerary
@package_price_bp.route('/itineraries/<int:itinerary_id>/prices', methods=['GET'])
def get_itinerary_prices(itinerary_id):
    try:
        is_active = request.args.get('is_active', 'true')
        
        query = PackagePrice.query.filter_by(itinerary_id=itinerary_id)
        
        if is_active.lower() in ['true', '1', 'yes']:
            query = query.filter_by(is_active=True)
        
        query = query.order_by(PackagePrice.valid_from.desc())
        package_prices = query.all()
        
        return jsonify({
            'itinerary_id': itinerary_id,
            'count': len(package_prices),
            'data': [price.to_dict() for price in package_prices]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Bulk create package prices
@package_price_bp.route('/package-prices/bulk', methods=['POST'])
def create_bulk_package_prices():
    try:
        data = request.get_json()
        
        if not isinstance(data, list):
            return jsonify({'error': 'Request body must be an array of package prices'}), 400
        
        created_prices = []
        
        for price_data in data:
            # Validate required fields for each price
            required_fields = [
                'package_id', 'itinerary_id', 
                'pax_2_price', 'pax_4_price', 'pax_6_price', 'pax_8_price',
                'valid_from', 'valid_to'
            ]
            missing_fields = [field for field in required_fields if field not in price_data]
            
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields in one of the items: {", ".join(missing_fields)}'
                }), 400
            
            # Convert dates
            try:
                valid_from = datetime.strptime(price_data['valid_from'], '%Y-%m-%d').date()
                valid_to = datetime.strptime(price_data['valid_to'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            
            # Check for overlapping periods
            overlapping_price = PackagePrice.query.filter(
                PackagePrice.package_id == price_data['package_id'],
                PackagePrice.itinerary_id == price_data['itinerary_id'],
                PackagePrice.valid_from <= valid_to,
                PackagePrice.valid_to >= valid_from
            ).first()
            
            if overlapping_price:
                continue  # Skip overlapping prices
            
            package_price = PackagePrice(
                package_id=price_data['package_id'],
                itinerary_id=price_data['itinerary_id'],
                pax_2_price=price_data['pax_2_price'],
                pax_4_price=price_data['pax_4_price'],
                pax_6_price=price_data['pax_6_price'],
                pax_8_price=price_data['pax_8_price'],
                single_supplement=price_data.get('single_supplement'),
                child_price=price_data.get('child_price'),
                includes=price_data.get('includes', []),
                excludes=price_data.get('excludes', []),
                valid_from=valid_from,
                valid_to=valid_to,
                is_active=price_data.get('is_active', True)
            )
            
            db.session.add(package_price)
            created_prices.append(package_price)
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_prices)} package prices created successfully',
            'data': [price.to_dict() for price in created_prices]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get price for specific date, package, and itinerary
@package_price_bp.route('/price-check', methods=['GET'])
def check_price():
    try:
        package_id = request.args.get('package_id')
        itinerary_id = request.args.get('itinerary_id')
        check_date = request.args.get('date', date.today().isoformat())
        
        if not package_id or not itinerary_id:
            return jsonify({'error': 'package_id and itinerary_id are required'}), 400
        
        try:
            check_date = datetime.strptime(check_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        price = PackagePrice.query.filter(
            PackagePrice.package_id == int(package_id),
            PackagePrice.itinerary_id == int(itinerary_id),
            PackagePrice.valid_from <= check_date,
            PackagePrice.valid_to >= check_date,
            PackagePrice.is_active == True
        ).order_by(PackagePrice.created_at.desc()).first()
        
        if not price:
            return jsonify({
                'message': 'No active price found for the specified date',
                'data': None
            }), 404
        
        return jsonify({
            'date': check_date.isoformat(),
            'data': price.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Toggle price active status
@package_price_bp.route('/package-prices/<int:price_id>/toggle-active', methods=['PATCH'])
def toggle_price_active(price_id):
    try:
        package_price = PackagePrice.query.get_or_404(price_id)
        
        package_price.is_active = not package_price.is_active
        
        db.session.commit()
        
        status = "activated" if package_price.is_active else "deactivated"
        
        return jsonify({
            'message': f'Package price {status} successfully',
            'data': package_price.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Calculate price for specific number of passengers
@package_price_bp.route('/package-prices/<int:price_id>/calculate', methods=['GET'])
def calculate_price(price_id):
    try:
        package_price = PackagePrice.query.get_or_404(price_id)
        
        adults = int(request.args.get('adults', 2))
        children = int(request.args.get('children', 0))
        single_rooms = int(request.args.get('single_rooms', 0))
        
        # Determine which price tier to use
        if adults <= 2:
            base_price = package_price.pax_2_price
        elif adults <= 4:
            base_price = package_price.pax_4_price
        elif adults <= 6:
            base_price = package_price.pax_6_price
        else:
            base_price = package_price.pax_8_price
        
        # Calculate total
        adult_total = base_price * adults
        child_total = package_price.child_price * children if package_price.child_price else 0
        single_supplement_total = package_price.single_supplement * single_rooms if package_price.single_supplement else 0
        
        total_price = adult_total + child_total + single_supplement_total
        
        return jsonify({
            'calculation': {
                'adults': adults,
                'children': children,
                'single_rooms': single_rooms,
                'base_price_per_adult': base_price,
                'child_price': package_price.child_price,
                'single_supplement': package_price.single_supplement,
                'adult_total': adult_total,
                'child_total': child_total,
                'single_supplement_total': single_supplement_total,
                'total_price': total_price
            },
            'price_details': package_price.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500