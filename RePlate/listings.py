from datetime import datetime

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user

from extensions import db
from models import Listing, CATEGORIES

bp = Blueprint("listings", __name__, url_prefix="/api/listings")


def listing_to_dict(listing, include_logs=False):
    data = {
        "id": listing.id,
        "title": listing.title,
        "description": listing.description,
        "category": listing.category,
        "quantity": listing.quantity,
        "unit": listing.unit,
        "expiry_date": listing.expiry_date.isoformat() if listing.expiry_date else None,
        "days_until_expiry": listing.days_until_expiry,
        "is_past_expiry": listing.is_past_expiry,
        "pickup_location": listing.pickup_location,
        "pickup_window_start": listing.pickup_window_start,
        "pickup_window_end": listing.pickup_window_end,
        "status": listing.status,
        "status_label": listing.status_label,
        "donor_id": listing.donor_id,
        "donor_name": listing.donor.name if listing.donor else None,
        "donor_organization": listing.donor.organization if listing.donor else None,
        "recipient_id": listing.recipient_id,
        "recipient_name": listing.recipient.name if listing.recipient else None,
        "volunteer_id": listing.volunteer_id,
        "volunteer_name": listing.volunteer.name if listing.volunteer else None,
        "created_at": listing.created_at.isoformat() if listing.created_at else None,
    }
    if include_logs:
        data["logs"] = [
            {
                "status": log.status,
                "status_label": log.status.replace("_", " ").title(),
                "note": log.note,
                "changed_by": log.changed_by.name if log.changed_by else None,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in listing.logs.order_by(db.desc("timestamp")).all()
        ]
    return data


@bp.route("/")
def browse():
    query = Listing.query

    status = request.args.get("status", "available")
    category = request.args.get("category", "")
    keyword = request.args.get("q", "").strip()

    if status and status != "all":
        query = query.filter(Listing.status == status)
    if category:
        query = query.filter(Listing.category == category)
    if keyword:
        query = query.filter(Listing.title.ilike(f"%{keyword}%"))

    query = query.order_by(Listing.expiry_date.asc(), Listing.created_at.desc())

    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=page, per_page=12, error_out=False)

    return jsonify({
        "listings": [listing_to_dict(listing) for listing in pagination.items],
        "categories": CATEGORIES,
        "status": status,
        "category": category,
        "keyword": keyword,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    })


@bp.route("/<int:listing_id>")
def detail(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    return jsonify({"listing": listing_to_dict(listing, include_logs=True)})


@bp.route("/", methods=["POST"])
@login_required
def create():
    if current_user.role != "donor":
        return jsonify({"errors": ["Only donor accounts can post listings."]}), 403

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    category = data.get("category") or "other"
    quantity = data.get("quantity")
    unit = (data.get("unit") or "servings").strip() or "servings"
    expiry_date = data.get("expiry_date") or ""
    pickup_location = (data.get("pickup_location") or "").strip()
    pickup_window_start = (data.get("pickup_window_start") or "").strip()
    pickup_window_end = (data.get("pickup_window_end") or "").strip()

    errors = []
    if not title:
        errors.append("Please give the listing a title.")
    if not description:
        errors.append("Please describe what is being donated.")
    if category not in CATEGORIES:
        errors.append("Please choose a valid category.")
    try:
        quantity_value = float(quantity)
        if quantity_value <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("Quantity needs to be a positive number.")
        quantity_value = None
    try:
        expiry_value = datetime.strptime(expiry_date, "%Y-%m-%d").date()
    except ValueError:
        errors.append("Please provide a valid best-by date.")
        expiry_value = None
    if not pickup_location:
        errors.append("Please provide a pickup location.")

    if errors:
        return jsonify({"errors": errors}), 400

    listing = Listing(
        title=title,
        description=description,
        category=category,
        quantity=quantity_value,
        unit=unit,
        expiry_date=expiry_value,
        pickup_location=pickup_location,
        pickup_window_start=pickup_window_start or None,
        pickup_window_end=pickup_window_end or None,
        donor=current_user,
        status="available",
    )
    db.session.add(listing)
    db.session.flush()
    listing.add_log("available", changed_by=current_user, note="Listing posted.")
    db.session.commit()
    return jsonify({"listing": listing_to_dict(listing), "message": "Listing posted. Recipients can claim it now."})


def _transition(listing, allowed_from, new_status, note):
    if listing.status not in allowed_from:
        return False
    listing.add_log(new_status, changed_by=current_user, note=note)
    db.session.commit()
    return True


@bp.route("/<int:listing_id>/claim", methods=["POST"])
@login_required
def claim(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if current_user.role != "recipient":
        return jsonify({"errors": ["Only recipient accounts can claim listings."]}), 403
    if listing.status != "available":
        return jsonify({"errors": ["This listing is no longer available."]}), 400

    listing.recipient = current_user
    if _transition(listing, {"available"}, "claimed", f"Claimed by {current_user.name}."):
        return jsonify({"listing": listing_to_dict(listing), "message": "Listing claimed. Coordinate pickup before the window closes."})
    return jsonify({"errors": ["That action no longer applies to this listing."]}), 400


@bp.route("/<int:listing_id>/release", methods=["POST"])
@login_required
def release(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.recipient_id != current_user.id:
        abort(403)
    listing.recipient = None
    if _transition(listing, {"claimed"}, "available", "Recipient released the claim."):
        return jsonify({"listing": listing_to_dict(listing), "message": "Claim released. The listing is available again."})
    return jsonify({"errors": ["That action no longer applies to this listing."]}), 400


@bp.route("/<int:listing_id>/accept", methods=["POST"])
@login_required
def accept(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if current_user.role != "volunteer":
        return jsonify({"errors": ["Only volunteer accounts can accept a delivery run."]}), 403
    if listing.volunteer_id is not None:
        return jsonify({"errors": ["A volunteer has already taken this delivery."]}), 400

    listing.volunteer = current_user
    if _transition(listing, {"claimed"}, "in_transit", f"Pickup accepted by volunteer {current_user.name}."):
        return jsonify({"listing": listing_to_dict(listing), "message": "Delivery accepted. Thank you for closing the loop."})
    return jsonify({"errors": ["That action no longer applies to this listing."]}), 400


@bp.route("/<int:listing_id>/deliver", methods=["POST"])
@login_required
def deliver(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    is_assigned_volunteer = listing.volunteer_id == current_user.id
    is_direct_recipient = listing.recipient_id == current_user.id and listing.volunteer_id is None

    if not (is_assigned_volunteer or is_direct_recipient):
        abort(403)

    if _transition(listing, {"in_transit", "claimed"}, "delivered", "Marked as delivered."):
        return jsonify({"listing": listing_to_dict(listing), "message": "Marked as delivered. Thank you for helping reduce food waste."})
    return jsonify({"errors": ["That action no longer applies to this listing."]}), 400


@bp.route("/<int:listing_id>/cancel", methods=["POST"])
@login_required
def cancel(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.donor_id != current_user.id:
        abort(403)
    if _transition(listing, {"available", "claimed", "in_transit"}, "cancelled", "Cancelled by donor."):
        return jsonify({"listing": listing_to_dict(listing), "message": "Listing cancelled."})
    return jsonify({"errors": ["That action no longer applies to this listing."]}), 400
