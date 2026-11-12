from flask import Blueprint, jsonify, make_response
from models import db, Farmer, Price, Broadcast

reports_bp = Blueprint('reports_bp', __name__)

@reports_bp.route('/reports/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    try:
        total_farmers = Farmer.query.count()
        total_prices = Price.query.count()
        total_broadcasts = Broadcast.query.count()

        stats = {
            "total_farmers": total_farmers,
            "total_prices_tracked": total_prices,
            "total_broadcasts_sent": total_broadcasts
        }
        return make_response(jsonify(stats), 200)
    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 500)
