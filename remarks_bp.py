from flask import Blueprint, request, jsonify
from models import db, CustomerRemark

remarks_bp = Blueprint('remarks', __name__)

# Submit a new customer remark (no login required)
@remarks_bp.route('/remarks', methods=['POST'])
def submit_remark():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['customer_name', 'customer_email', 'tour_package', 'remark', 'rating']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"{field} is required"}), 400
        
        # Validate rating (1-5)
        rating = data.get('rating')
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({"message": "Rating must be an integer between 1 and 5"}), 400
        
        # Validate email format
        email = data.get('customer_email')
        if '@' not in email or '.' not in email:
            return jsonify({"message": "Please provide a valid email address"}), 400
        
        # Create new remark (auto-approved since no admin panel)
        new_remark = CustomerRemark(
            customer_name=data.get('customer_name'),
            customer_email=data.get('customer_email'),
            customer_phone=data.get('customer_phone', ''),
            tour_package=data.get('tour_package'),
            remark=data.get('remark'),
            rating=rating,
            is_approved=True  # Auto-approve all remarks
        )
        
        db.session.add(new_remark)
        db.session.commit()
        
        return jsonify({
            "message": "Thank you for your feedback! Your remark has been submitted successfully.",
            "remark": new_remark.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error submitting remark: {str(e)}"}), 500

# Get all remarks (public - no login required)
@remarks_bp.route('/remarks', methods=['GET'])
def get_remarks():
    try:
        # Get query parameters for filtering
        tour_package = request.args.get('tour_package')
        min_rating = request.args.get('min_rating', type=int)
        
        # Start with all approved remarks
        query = CustomerRemark.query.filter_by(is_approved=True)
        
        # Apply filters if provided
        if tour_package:
            query = query.filter(CustomerRemark.tour_package.ilike(f'%{tour_package}%'))
        if min_rating:
            query = query.filter(CustomerRemark.rating >= min_rating)
        
        # Order by date (newest first)
        remarks = query.order_by(CustomerRemark.remark_date.desc()).all()
        
        return jsonify({
            "remarks": [remark.to_dict() for remark in remarks],
            "total": len(remarks)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Error fetching remarks: {str(e)}"}), 500

# Get remark statistics (public - no login required)
@remarks_bp.route('/remarks/stats', methods=['GET'])
def get_remark_stats():
    try:
        total_remarks = CustomerRemark.query.filter_by(is_approved=True).count()
        
        # Average rating
        avg_rating_result = db.session.query(db.func.avg(CustomerRemark.rating)).filter_by(is_approved=True).scalar()
        avg_rating = round(avg_rating_result, 1) if avg_rating_result else 0
        
        # Rating distribution
        rating_distribution = {}
        for i in range(1, 6):
            count = CustomerRemark.query.filter_by(is_approved=True, rating=i).count()
            rating_distribution[str(i)] = count
        
        # Popular tour packages
        tour_stats = db.session.query(
            CustomerRemark.tour_package,
            db.func.count(CustomerRemark.id).label('count'),
            db.func.avg(CustomerRemark.rating).label('avg_rating')
        ).filter_by(is_approved=True).group_by(CustomerRemark.tour_package).all()
        
        popular_tours = []
        for tour in tour_stats:
            popular_tours.append({
                'tour_package': tour.tour_package,
                'count': tour.count,
                'avg_rating': round(tour.avg_rating, 1) if tour.avg_rating else 0
            })
        
        return jsonify({
            "total_remarks": total_remarks,
            "average_rating": avg_rating,
            "rating_distribution": rating_distribution,
            "popular_tours": popular_tours
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Error fetching statistics: {str(e)}"}), 500

# Get a single remark by ID (public - no login required)
@remarks_bp.route('/remarks/<int:remark_id>', methods=['GET'])
def get_single_remark(remark_id):
    try:
        remark = CustomerRemark.query.filter_by(id=remark_id, is_approved=True).first()
        if not remark:
            return jsonify({"message": "Remark not found"}), 404
        
        return jsonify({
            "remark": remark.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Error fetching remark: {str(e)}"}), 500