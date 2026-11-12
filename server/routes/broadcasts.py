from flask import Blueprint, request, jsonify, make_response
from models import db, Broadcast

broadcasts_bp = Blueprint('broadcasts_bp', __name__)

@broadcasts_bp.route('/broadcasts', methods=['GET'])
def get_broadcasts():
    broadcasts = Broadcast.query.all()
    return make_response(jsonify([b.to_dict() for b in broadcasts]), 200)

@broadcasts_bp.route('/broadcasts', methods=['POST'])
def create_broadcast():
    data = request.get_json()
    try:
        new_broadcast = Broadcast(
            message=data.get('message'),
            recipient_group=data.get('recipient_group')
        )
        db.session.add(new_broadcast)
        db.session.commit()
        return make_response(jsonify(new_broadcast.to_dict()), 201)
    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 400)
