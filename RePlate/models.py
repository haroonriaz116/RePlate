"""Database models for RePlate.

Three tables back the platform. ``User`` covers all three roles that the
resume bullet describes, donor, recipient, and volunteer, distinguished by
a ``role`` column rather than separate tables, since the three roles share
every field they need. ``Listing`` is a single food donation post and
carries the fields needed to manage it from creation through pickup.
``StatusLog`` is an append only audit trail so that every change to a
listing's status is recorded rather than overwritten, which is what makes
donation tracking auditable instead of just a single mutable field.

Indexes are placed on the columns that the browse and dashboard queries
filter or sort by (status, category, expiry date, and the foreign keys
that join listings back to users) so that lookups stay fast as the number
of listings grows well past the 200 mark referenced on the resume.
"""
from datetime import datetime, date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

ROLES = ("donor", "recipient", "volunteer")

STATUSES = ("available", "claimed", "in_transit", "delivered", "cancelled", "expired")

STATUS_LABELS = {
    "available": "Available",
    "claimed": "Claimed",
    "in_transit": "In Transit",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
    "expired": "Expired",
}

CATEGORIES = (
    "produce",
    "bakery",
    "dairy",
    "prepared",
    "pantry",
    "frozen",
    "other",
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    organization = db.Column(db.String(180))
    location = db.Column(db.String(180))
    phone = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    listings_donated = db.relationship(
        "Listing", foreign_keys="Listing.donor_id", back_populates="donor", lazy="dynamic"
    )
    listings_claimed = db.relationship(
        "Listing", foreign_keys="Listing.recipient_id", back_populates="recipient", lazy="dynamic"
    )
    listings_delivering = db.relationship(
        "Listing", foreign_keys="Listing.volunteer_id", back_populates="volunteer", lazy="dynamic"
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def role_label(self):
        return self.role.capitalize()

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Listing(db.Model):
    __tablename__ = "listings"
    __table_args__ = (
        db.Index("ix_listings_status_category", "status", "category"),
        db.Index("ix_listings_expiry", "expiry_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False, default="other")
    quantity = db.Column(db.Float, nullable=False, default=1)
    unit = db.Column(db.String(30), nullable=False, default="servings")
    expiry_date = db.Column(db.Date, nullable=False)
    pickup_location = db.Column(db.String(220), nullable=False)
    pickup_window_start = db.Column(db.String(60))
    pickup_window_end = db.Column(db.String(60))
    status = db.Column(db.String(20), nullable=False, default="available", index=True)

    donor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    donor = db.relationship("User", foreign_keys=[donor_id], back_populates="listings_donated")
    recipient = db.relationship("User", foreign_keys=[recipient_id], back_populates="listings_claimed")
    volunteer = db.relationship("User", foreign_keys=[volunteer_id], back_populates="listings_delivering")

    logs = db.relationship(
        "StatusLog", back_populates="listing", order_by="StatusLog.timestamp", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    @property
    def status_label(self):
        return STATUS_LABELS.get(self.status, self.status.title())

    @property
    def is_past_expiry(self):
        return self.expiry_date is not None and self.expiry_date < date.today()

    @property
    def days_until_expiry(self):
        if self.expiry_date is None:
            return None
        return (self.expiry_date - date.today()).days

    def add_log(self, status, changed_by, note=None):
        entry = StatusLog(listing=self, status=status, changed_by_id=changed_by.id, note=note)
        self.status = status
        db.session.add(entry)
        return entry

    def __repr__(self):
        return f"<Listing {self.id} {self.title!r} [{self.status}]>"


class StatusLog(db.Model):
    """One row per status transition, the audit trail behind donation tracking."""

    __tablename__ = "status_logs"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    note = db.Column(db.String(280))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    listing = db.relationship("Listing", back_populates="logs")
    changed_by = db.relationship("User")
