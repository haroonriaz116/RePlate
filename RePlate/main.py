from flask import Blueprint, jsonify

from models import Listing, User
from listings import listing_to_dict

bp = Blueprint("main", __name__, url_prefix="/api")


@bp.route("/home")
def home():
    stats = {
        "active_listings": Listing.query.filter_by(status="available").count(),
        "total_listings": Listing.query.count(),
        "completed": Listing.query.filter_by(status="delivered").count(),
        "volunteers": User.query.filter_by(role="volunteer").count(),
    }
    recent = (
        Listing.query.filter_by(status="available")
        .order_by(Listing.expiry_date.asc())
        .limit(6)
        .all()
    )
    return jsonify({"stats": stats, "recent": [listing_to_dict(l) for l in recent]})
