from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Story, User, Lodge
from datetime import datetime

stories_bp = Blueprint('stories', __name__)

def is_admin_or_deputy():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user and (user.is_admin or user.is_deputy)

@stories_bp.route('/', methods=['GET'])
def get_stories():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    stories = Story.query.filter_by(is_active=True)\
        .order_by(Story.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'stories': [{
            'id': story.id,
            'title': story.title,
            'excerpt': story.content[:200] + '...' if len(story.content) > 200 else story.content,
            'author': story.author.username,
            'lodge_name': story.lodge.name if story.lodge else None,
            'featured_image': story.featured_image,
            'category': story.category,
            'views': story.views,
            'created_at': story.created_at.isoformat()
        } for story in stories.items],
        'total': stories.total,
        'pages': stories.pages,
        'current_page': stories.page
    }), 200

@stories_bp.route('/<int:story_id>', methods=['GET'])
def get_story(story_id):
    story = Story.query.get(story_id)
    if not story or not story.is_active:
        return jsonify({'error': 'Story not found'}), 404
    
    # Increment view count
    story.views += 1
    db.session.commit()
    
    return jsonify({
        'story': {
            'id': story.id,
            'title': story.title,
            'content': story.content,
            'author': {
                'id': story.author.id,
                'username': story.author.username,
                'profile_picture': story.author.profile_picture
            },
            'lodge': {
                'id': story.lodge.id,
                'name': story.lodge.name
            } if story.lodge else None,
            'featured_image': story.featured_image,
            'video_url': story.video_url,
            'category': story.category,
            'tags': story.tags or [],
            'is_featured': story.is_featured,
            'views': story.views,
            'created_at': story.created_at.isoformat(),
            'updated_at': story.updated_at.isoformat()
        }
    }), 200

@stories_bp.route('/', methods=['POST'])
@jwt_required()
def create_story():
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    user_id = get_jwt_identity()
    
    required_fields = ['title', 'content']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    story = Story(
        title=data['title'],
        content=data['content'],
        author_id=user_id,
        lodge_id=data.get('lodge_id'),
        featured_image=data.get('featured_image'),
        video_url=data.get('video_url'),
        category=data.get('category', 'general'),
        tags=data.get('tags', []),
        is_featured=data.get('is_featured', False),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.session.add(story)
    db.session.commit()
    
    return jsonify({
        'message': 'Story created successfully',
        'story': {
            'id': story.id,
            'title': story.title
        }
    }), 201

@stories_bp.route('/<int:story_id>', methods=['PUT'])
@jwt_required()
def update_story(story_id):
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    story = Story.query.get(story_id)
    if not story:
        return jsonify({'error': 'Story not found'}), 404
    
    # Check if user is author or admin/deputy
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if story.author_id != user_id and not (user.is_admin or user.is_deputy):
        return jsonify({'error': 'Unauthorized to edit this story'}), 403
    
    data = request.get_json()
    
    if 'title' in data:
        story.title = data['title']
    
    if 'content' in data:
        story.content = data['content']
    
    if 'lodge_id' in data:
        story.lodge_id = data['lodge_id']
    
    if 'featured_image' in data:
        story.featured_image = data['featured_image']
    
    if 'video_url' in data:
        story.video_url = data['video_url']
    
    if 'category' in data:
        story.category = data['category']
    
    if 'tags' in data:
        story.tags = data['tags']
    
    if 'is_featured' in data:
        story.is_featured = data['is_featured']
    
    story.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Story updated successfully',
        'story': {
            'id': story.id,
            'title': story.title,
            'updated_at': story.updated_at.isoformat()
        }
    }), 200

@stories_bp.route('/<int:story_id>', methods=['DELETE'])
@jwt_required()
def delete_story(story_id):
    if not is_admin_or_deputy():
        return jsonify({'error': 'Unauthorized'}), 403
    
    story = Story.query.get(story_id)
    if not story:
        return jsonify({'error': 'Story not found'}), 404
    
    # Check if user is author or admin/deputy
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if story.author_id != user_id and not (user.is_admin or user.is_deputy):
        return jsonify({'error': 'Unauthorized to delete this story'}), 403
    
    # Soft delete
    story.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'Story deleted successfully'}), 200

@stories_bp.route('/featured', methods=['GET'])
def get_featured_stories():
    stories = Story.query.filter_by(is_active=True, is_featured=True)\
        .order_by(Story.created_at.desc())\
        .limit(5)\
        .all()
    
    return jsonify({
        'stories': [{
            'id': story.id,
            'title': story.title,
            'excerpt': story.content[:150] + '...' if len(story.content) > 150 else story.content,
            'featured_image': story.featured_image,
            'author': story.author.username,
            'created_at': story.created_at.isoformat()
        } for story in stories]
    }), 200