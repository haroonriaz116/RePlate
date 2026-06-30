"""Shared extension instances.

Kept in their own module so that models.py, app.py, and the blueprints can
all import the same SQLAlchemy and LoginManager objects without circular
imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "info"
