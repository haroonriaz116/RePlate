from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from models import Listing
from listings import listing_to_dict

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.route("/")
@login_required
def home():
    if current_user.role == "donor":
        listings = current_user.listings_donated.order_by(Listing.created_at.desc()).all()
        counts = {
            "available": sum(1 for l in listings if l.status == "available"),
            "in_progress": sum(1 for l in listings if l.status in ("claimed", "in_transit")),
            "delivered": sum(1 for l in listings if l.status == "delivered"),
        }
        return jsonify({
            "role": "donor",
            "listings": [listing_to_dict(l) for l in listings],
            "counts": counts,
        })

    if current_user.role == "recipient":
        listings = current_user.listings_claimed.order_by(Listing.created_at.desc()).all()
        return jsonify({"role": "recipient", "listings": [listing_to_dict(l) for l in listings]})

    if current_user.role == "volunteer":
        open_runs_query = Listing.query.filter_by(status="claimed", volunteer_id=None)
        open_runs_total = open_runs_query.count()
        available_runs = open_runs_query.order_by(Listing.expiry_date.asc()).limit(15).all()
        my_runs = current_user.listings_delivering.order_by(Listing.created_at.desc()).all()
        return jsonify({
            "role": "volunteer",
            "available_runs": [listing_to_dict(l) for l in available_runs],
            "open_runs_total": open_runs_total,
            "my_runs": [listing_to_dict(l) for l in my_runs],
        })

    return jsonify({"role": current_user.role, "listings": []})
