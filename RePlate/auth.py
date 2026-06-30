from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User, ROLES

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def user_to_dict(user):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "role_label": user.role_label,
        "organization": user.organization,
        "location": user.location,
        "phone": user.phone,
    }


@bp.route("/me")
def me():
    if current_user.is_authenticated:
        return jsonify({"user": user_to_dict(current_user)})
    return jsonify({"user": None})


@bp.route("/register", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return jsonify({"errors": ["You are already signed in."]}), 400

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role") or ""
    organization = (data.get("organization") or "").strip()
    location = (data.get("location") or "").strip()
    phone = (data.get("phone") or "").strip()

    errors = []
    if not name:
        errors.append("Please enter your name.")
    if not email or "@" not in email:
        errors.append("Please enter a valid email address.")
    if len(password) < 8:
        errors.append("Passwords need to be at least 8 characters.")
    if role not in ROLES:
        errors.append("Please choose a role.")
    if email and User.query.filter_by(email=email).first():
        errors.append("An account with that email already exists.")

    if errors:
        return jsonify({"errors": errors}), 400

    user = User(
        name=name,
        email=email,
        role=role,
        organization=organization or None,
        location=location or None,
        phone=phone or None,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"user": user_to_dict(user), "message": f"Welcome to RePlate, {user.name.split()[0]}."})


@bp.route("/login", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return jsonify({"errors": ["You are already signed in."]}), 400

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()

    if user is None or not user.check_password(password):
        return jsonify({"errors": ["That email and password combination did not match."]}), 401

    login_user(user)
    return jsonify({"user": user_to_dict(user), "message": f"Welcome back, {user.name.split()[0]}."})


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "You have been logged out."})
