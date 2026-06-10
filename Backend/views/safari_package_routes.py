# views/safari_package_routes.py - UPDATED VERSION

from flask import Blueprint, request, jsonify
from datetime import datetime, date
from models import SafariPackage, PackageDay, PackageItinerary, ItineraryAccommodation, PackagePrice
from extensions import db

safari_card_bp = Blueprint('safari_cards', __name__)

# CREATE - Save safari package from frontend card (WITH ITINERARY AND PRICES)
@safari_card_bp.route('/safari-cards', methods=['POST'])
def create_safari_card():
    try:
        data = request.get_json()
        print("📥 Received safari card data:", data)
        
        # Validate required fields
        required_fields = ['name', 'description', 'duration', 'priceOptions']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Check if package name already exists
        existing_package = SafariPackage.query.filter_by(name=data['name']).first()
        if existing_package:
            return jsonify({'error': 'Package with this name already exists'}), 409
        
        # Calculate total_days from duration string
        duration_str = data['duration']
        try:
            # Extract days from string like "5-7 days recommended"
            import re
            days_match = re.search(r'(\d+)[-–](\d+)', duration_str)
            if days_match:
                min_days = int(days_match.group(1))
                max_days = int(days_match.group(2))
                total_days = max_days  # Use maximum days
            else:
                total_days = 5  # Default
        except:
            total_days = 5
        
        # 1. Create new safari package
        safari_package = SafariPackage(
            name=data['name'],
            description=data['description'],
            total_days=total_days,
            total_nights=total_days - 1,
            is_active=True
        )
        
        db.session.add(safari_package)
        db.session.flush()  # Get the ID without committing
        
        # 2. Create package days from itinerary (if provided)
        if 'itinerary' in data and data['itinerary']:
            itinerary_text = data['itinerary']
            # Parse itinerary into days
            import re
            day_pattern = r'Day\s+(\d+):\s*(.+)'
            days_found = re.findall(day_pattern, itinerary_text, re.IGNORECASE)
            
            if days_found:
                for day_num, day_desc in days_found:
                    package_day = PackageDay(
                        package_id=safari_package.id,
                        day_number=int(day_num),
                        title=f"Day {day_num}",
                        description=day_desc,
                        activities=[],
                        meals=['Breakfast', 'Lunch', 'Dinner'],
                        park_name="Maasai Mara",  # Default, can be extracted
                        park_description=""
                    )
                    db.session.add(package_day)
            else:
                # Create default days if no day pattern found
                for day_num in range(1, total_days + 1):
                    package_day = PackageDay(
                        package_id=safari_package.id,
                        day_number=day_num,
                        title=f"Day {day_num}",
                        description=f"Day {day_num} of your safari adventure",
                        activities=['Game drives', 'Wildlife viewing'],
                        meals=['Breakfast', 'Lunch', 'Dinner'],
                        park_name="Maasai Mara",
                        park_description=""
                    )
                    db.session.add(package_day)
        else:
            # Create default days if no itinerary provided
            for day_num in range(1, total_days + 1):
                package_day = PackageDay(
                    package_id=safari_package.id,
                    day_number=day_num,
                    title=f"Day {day_num}",
                    description=f"Day {day_num} of your safari adventure",
                    activities=['Game drives', 'Wildlife viewing'],
                    meals=['Breakfast', 'Lunch', 'Dinner'],
                    park_name="Maasai Mara",
                    park_description=""
                )
                db.session.add(package_day)
        
        # 3. Create default itinerary
        default_itinerary = PackageItinerary(
            package_id=safari_package.id,
            itinerary_code="STANDARD",
            name="Standard Itinerary",
            description=data.get('description', ''),
            is_default=True
        )
        db.session.add(default_itinerary)
        db.session.flush()
        
        # 4. Create accommodations for each day
        for day_num in range(1, total_days + 1):
            accommodation = ItineraryAccommodation(
                itinerary_id=default_itinerary.id,
                day_number=day_num,
                accommodation_name="Selected Lodge"  # Would come from frontend
            )
            db.session.add(accommodation)
        
        # 5. Create package price entries from priceOptions
        if 'priceOptions' in data and data['priceOptions']:
            price_options = data['priceOptions']
            
            # Calculate prices for standard groups (2,4,6,8 pax)
            def find_closest_price(num_people, options):
                # First try exact match
                for option in options:
                    if option.get('people') == num_people:
                        return float(option.get('price', 300))
                # If not found, find closest
                sorted_options = sorted(options, key=lambda x: abs(x.get('people', 2) - num_people))
                return float(sorted_options[0].get('price', 300)) if sorted_options else 300
            
            today = date.today()
            end_date = datetime(today.year + 1, today.month, today.day).date()
            
            # Get price values
            pax_2_price = find_closest_price(2, price_options)
            pax_4_price = find_closest_price(4, price_options)
            pax_6_price = find_closest_price(6, price_options)
            pax_8_price = find_closest_price(8, price_options)
            
            # Create package price with the EXACT fields you specified
            package_price = PackagePrice(
                package_id=safari_package.id,
                itinerary_id=default_itinerary.id,
                pax_2_price=pax_2_price,
                pax_4_price=pax_4_price,
                pax_6_price=pax_6_price,
                pax_8_price=pax_8_price,
                single_supplement=pax_2_price * 0.5,  # 50% of 2 pax price
                child_price=pax_2_price * 0.6,  # 60% of 2 pax price
                includes=['Accommodation', 'Meals', 'Game Drives', 'Park Fees'],
                excludes=['International Flights', 'Travel Insurance', 'Tips'],
                valid_from=today,
                valid_to=end_date,
                is_active=True
            )
            db.session.add(package_price)
        
        # 6. Commit everything
        db.session.commit()
        
        print(f"✅ Safari package created with ID: {safari_package.id}")
        print(f"✅ Itinerary created with ID: {default_itinerary.id}")
        print(f"✅ Price created for 2,4,6,8 pax: {pax_2_price}, {pax_4_price}, {pax_6_price}, {pax_8_price}")
        
        # Get full package data with relationships
        full_package = SafariPackage.query.get(safari_package.id)
        
        return jsonify({
            'success': True,
            'message': 'Safari package saved to database successfully',
            'data': full_package.to_dict(),
            'package_id': safari_package.id,
            'itinerary_id': default_itinerary.id if default_itinerary else None,
            'prices': {
                'pax_2_price': pax_2_price,
                'pax_4_price': pax_4_price,
                'pax_6_price': pax_6_price,
                'pax_8_price': pax_8_price
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating safari package: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# CREATE PRICE for existing package (standalone endpoint)
@safari_card_bp.route('/package-prices', methods=['POST'])
def create_package_price():
    """Create a package price with 2,4,6,8 pax prices"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = [
            'package_id', 'itinerary_id', 
            'pax_2_price', 'pax_4_price', 'pax_6_price', 'pax_8_price'
        ]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Convert date strings to date objects
        today = date.today()
        try:
            valid_from = datetime.strptime(data.get('valid_from', today.isoformat()), '%Y-%m-%d').date()
            valid_to = datetime.strptime(data.get('valid_to', today.replace(year=today.year + 1).isoformat()), '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Check for overlapping price periods
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
            pax_2_price=float(data['pax_2_price']),
            pax_4_price=float(data['pax_4_price']),
            pax_6_price=float(data['pax_6_price']),
            pax_8_price=float(data['pax_8_price']),
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
            'success': True,
            'message': 'Package price created successfully',
            'data': package_price.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# CREATE ITINERARY for existing package
@safari_card_bp.route('/package-itineraries', methods=['POST'])
def create_package_itinerary():
    """Create a package itinerary"""
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
        
        # If setting as default, unset any existing default
        if data.get('is_default', False):
            PackageItinerary.query.filter_by(
                package_id=data['package_id'],
                is_default=True
            ).update({'is_default': False})
        
        # Create itinerary
        itinerary = PackageItinerary(
            package_id=data['package_id'],
            itinerary_code=data['itinerary_code'],
            name=data['name'],
            description=data.get('description'),
            is_default=data.get('is_default', False)
        )
        
        db.session.add(itinerary)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Package itinerary created successfully',
            'data': itinerary.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# READ - Get all safari packages
@safari_card_bp.route('/safari-cards', methods=['GET'])
def get_all_safari_cards():
    try:
        safari_packages = SafariPackage.query.filter_by(is_active=True)\
            .order_by(SafariPackage.created_at.desc())\
            .all()
        
        packages_data = []
        for package in safari_packages:
            package_dict = package.to_dict()
            packages_data.append(package_dict)
        
        return jsonify({
            'success': True,
            'count': len(safari_packages),
            'data': packages_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Get single safari package with details
@safari_card_bp.route('/safari-cards/<int:package_id>', methods=['GET'])
def get_safari_card(package_id):
    try:
        safari_package = SafariPackage.query.get_or_404(package_id)
        
        return jsonify({
            'success': True,
            'data': safari_package.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# UPDATE - Update safari package
@safari_card_bp.route('/safari-cards/<int:package_id>', methods=['PUT'])
def update_safari_card(package_id):
    try:
        safari_package = SafariPackage.query.get_or_404(package_id)
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            safari_package.name = data['name']
        if 'description' in data:
            safari_package.description = data['description']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Safari package updated successfully',
            'data': safari_package.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# DELETE - Delete safari package (soft delete)
@safari_card_bp.route('/safari-cards/<int:package_id>', methods=['DELETE'])
def delete_safari_card(package_id):
    try:
        safari_package = SafariPackage.query.get_or_404(package_id)
        
        # Soft delete (set inactive)
        safari_package.is_active = False
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Safari package deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Sync local storage with backend
@safari_card_bp.route('/safari-cards/sync', methods=['POST'])
def sync_safari_cards():
    try:
        data = request.get_json()
        
        if 'packages' not in data:
            return jsonify({'error': 'No packages data provided'}), 400
        
        local_packages = data['packages']
        synced_count = 0
        
        for local_package in local_packages:
            # Check if package already exists
            existing = SafariPackage.query.filter_by(name=local_package['name']).first()
            
            if not existing:
                try:
                    # Create new package from local storage
                    safari_package = SafariPackage(
                        name=local_package['name'],
                        description=local_package.get('description', ''),
                        total_days=5,  # Default
                        total_nights=4,
                        is_active=True
                    )
                    db.session.add(safari_package)
                    db.session.flush()
                    
                    # Create itinerary
                    itinerary = PackageItinerary(
                        package_id=safari_package.id,
                        itinerary_code="SYNCED",
                        name="Synced Itinerary",
                        description=local_package.get('description', ''),
                        is_default=True
                    )
                    db.session.add(itinerary)
                    db.session.flush()
                    
                    # Create price if priceOptions exist
                    if 'priceOptions' in local_package and local_package['priceOptions']:
                        # Calculate prices
                        def find_price(num_people, options):
                            for opt in options:
                                if opt.get('people') == num_people:
                                    return float(opt.get('price', 300))
                            return 300.0
                        
                        today = date.today()
                        end_date = datetime(today.year + 1, today.month, today.day).date()
                        
                        price = PackagePrice(
                            package_id=safari_package.id,
                            itinerary_id=itinerary.id,
                            pax_2_price=find_price(2, local_package['priceOptions']),
                            pax_4_price=find_price(4, local_package['priceOptions']),
                            pax_6_price=find_price(6, local_package['priceOptions']),
                            pax_8_price=find_price(8, local_package['priceOptions']),
                            valid_from=today,
                            valid_to=end_date,
                            is_active=True
                        )
                        db.session.add(price)
                    
                    synced_count += 1
                    
                except Exception as e:
                    print(f"Error syncing package {local_package.get('name')}: {e}")
                    continue
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Synced {synced_count} packages to backend',
            'synced_count': synced_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# GET package with full details
@safari_card_bp.route('/safari-cards/<int:package_id>/full', methods=['GET'])
def get_safari_card_full(package_id):
    try:
        safari_package = SafariPackage.query.get_or_404(package_id)
        
        # Get all related data
        package_data = safari_package.to_dict()
        
        # Get days
        days = PackageDay.query.filter_by(package_id=package_id).order_by(PackageDay.day_number).all()
        package_data['days'] = [day.to_dict() for day in days]
        
        # Get itineraries
        itineraries = PackageItinerary.query.filter_by(package_id=package_id).all()
        package_data['itineraries'] = [itinerary.to_dict() for itinerary in itineraries]
        
        # Get prices
        prices = PackagePrice.query.filter_by(package_id=package_id).all()
        package_data['prices'] = [price.to_dict() for price in prices]
        
        return jsonify({
            'success': True,
            'data': package_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404