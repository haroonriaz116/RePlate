"""Populate RePlate with realistic demo data.

Running this script wipes and rebuilds the SQLite database with a roster of
donors, recipients, and volunteers, and just over two hundred listings
spread across every status and category. That volume is what the resume
bullet about supporting 200+ active listings refers to, and seeding it for
real, rather than asserting it, is the point of building this for real.

Usage:
    python seed.py
"""
import random
from datetime import datetime, timedelta, date

from app import create_app
from extensions import db
from models import User, Listing, StatusLog

random.seed(42)

FIRST_NAMES = [
    "Amara", "Liam", "Sofia", "Noah", "Priya", "Ethan", "Mei", "Lucas",
    "Fatima", "Owen", "Yuki", "Mason", "Aaliyah", "Jacob", "Ines", "Caleb",
    "Zara", "Daniel", "Nadia", "Ryan", "Leila", "Marcus", "Anya", "Felix",
    "Chioma", "Tomas", "Grace", "Hassan", "Olivia", "Theo",
]
LAST_NAMES = [
    "Okafor", "Bennett", "Rossi", "Nguyen", "Patel", "Carter", "Sato",
    "Mendes", "Khalil", "Brooks", "Tanaka", "Reyes", "Larsen", "Osei",
    "Petit", "Singh", "Walsh", "Fischer", "Adeyemi", "Moreno",
]

DONOR_ORGS = [
    "Maple Street Bakery", "Greenleaf Grocers", "Harvest Table Catering",
    "Northside Diner", "Campus Dining Hall", "Sunrise Farmers Market",
    "Cornerstone Cafe", "Riverside Bistro", "Oakwood Grocery Co-op",
    "Daily Grain Bakery", "Union Street Kitchen", "Birchwood Cafeteria",
]

RECIPIENT_ORGS = [
    "Hopewell Shelter", "Community Fridge Network", "Lakeside Food Bank",
    "Outreach Centre", "Neighbours Helping Neighbours", "Westside Family Shelter",
    "Open Table Pantry", "Grace Community Kitchen", "Riverbend Drop-in Centre",
]

LOCATIONS = [
    "118 King St, Downtown", "44 Mill Lane, Riverside", "9 Orchard Ave, Westside",
    "256 Birch Rd, Northgate", "12 Elm Court, Old Town", "75 Harbour St, Dockside",
    "300 College Ave, Campus District", "8 Maple Cres, Southfield",
    "61 Union St, Midtown", "150 Garden Row, Eastside",
]

FOOD_ITEMS = {
    "produce": [
        "Crate of mixed vegetables", "Bruised but good apples",
        "End-of-day farmers market produce", "Surplus salad greens",
        "Box of ripe bananas", "Mixed root vegetable bin",
    ],
    "bakery": [
        "Day-old sourdough loaves", "Leftover bagels", "Unsold pastries",
        "Dozen day-old croissants", "Bread ends and heels", "Surplus dinner rolls",
    ],
    "dairy": [
        "Yogurt nearing best-by", "Milk close to date", "Block cheese ends",
        "Surplus cottage cheese", "Butter overstock",
    ],
    "prepared": [
        "Catering trays from a cancelled event", "Unused banquet meals",
        "Cafeteria surplus trays", "Restaurant overproduction", "Boxed lunch surplus",
    ],
    "pantry": [
        "Canned goods overstock", "Dry pasta surplus", "Rice bags, dented boxes",
        "Boxed cereal overstock", "Shelf-stable soup cans",
    ],
    "frozen": [
        "Frozen meal trays", "Surplus frozen vegetables", "Freezer clearance bread",
        "Frozen soup portions",
    ],
    "other": [
        "Mixed grocery rescue", "Assorted shelf-stable donation", "Mixed surplus box",
    ],
}

UNITS = {
    "produce": ("lbs", (5, 40)),
    "bakery": ("loaves", (4, 30)),
    "dairy": ("units", (6, 40)),
    "prepared": ("trays", (2, 15)),
    "pantry": ("cans", (10, 80)),
    "frozen": ("lbs", (5, 30)),
    "other": ("boxes", (1, 10)),
}

DESCRIPTIONS = [
    "Stored cold, never out longer than two hours. Bring your own containers if you can.",
    "Packed and ready to go, just needs a quick pickup before close.",
    "Still well within safe use, just over our shelf-life cutoff for sale.",
    "From today's service, more than we can hold over for tomorrow.",
    "Good condition, set aside as soon as we knew it would not sell.",
    "Cancelled order, never served, kept refrigerated since this morning.",
]


def rand_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def make_users():
    donors, recipients, volunteers = [], [], []

    for org in DONOR_ORGS:
        u = User(
            name=rand_name(),
            email=f"{org.lower().replace(' ', '.')}@replate.demo",
            role="donor",
            organization=org,
            location=random.choice(LOCATIONS),
            phone=f"555-{random.randint(200,999)}-{random.randint(1000,9999)}",
        )
        u.set_password("ReplateDemo123")
        donors.append(u)

    for org in RECIPIENT_ORGS:
        u = User(
            name=rand_name(),
            email=f"{org.lower().replace(' ', '.').replace(chr(39), '')}@replate.demo",
            role="recipient",
            organization=org,
            location=random.choice(LOCATIONS),
            phone=f"555-{random.randint(200,999)}-{random.randint(1000,9999)}",
        )
        u.set_password("ReplateDemo123")
        recipients.append(u)

    for i in range(14):
        name = rand_name()
        u = User(
            name=name,
            email=f"{name.lower().replace(' ', '.')}{i}@replate.demo",
            role="volunteer",
            location=random.choice(LOCATIONS),
            phone=f"555-{random.randint(200,999)}-{random.randint(1000,9999)}",
        )
        u.set_password("ReplateDemo123")
        volunteers.append(u)

    db.session.add_all(donors + recipients + volunteers)
    db.session.commit()
    return donors, recipients, volunteers


def build_listing(donor, status_plan, recipients, volunteers, now):
    category = random.choice(list(FOOD_ITEMS.keys()))
    title = random.choice(FOOD_ITEMS[category])
    unit, qty_range = UNITS[category]
    quantity = round(random.uniform(*qty_range), 1)

    days_ago = random.randint(0, 21)
    created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))

    if status_plan == "expired":
        expiry_date = (created_at - timedelta(days=random.randint(1, 4))).date()
    elif status_plan == "available":
        expiry_date = (now + timedelta(days=random.randint(0, 7))).date()
    else:
        expiry_date = (created_at + timedelta(days=random.randint(1, 9))).date()
        if expiry_date < date.today():
            expiry_date = date.today() + timedelta(days=random.randint(1, 5))

    listing = Listing(
        title=title,
        description=random.choice(DESCRIPTIONS),
        category=category,
        quantity=quantity,
        unit=unit,
        expiry_date=expiry_date,
        pickup_location=donor.location or random.choice(LOCATIONS),
        pickup_window_start=random.choice(["10:00 AM", "1:00 PM", "4:00 PM", "5:30 PM"]),
        pickup_window_end=random.choice(["12:00 PM", "3:00 PM", "6:00 PM", "8:00 PM"]),
        donor=donor,
        status="available",
        created_at=created_at,
        updated_at=created_at,
    )
    db.session.add(listing)
    db.session.flush()

    t = created_at
    listing.logs.append(StatusLog(status="available", changed_by_id=donor.id,
                                   note="Listing posted.", timestamp=t))

    if status_plan == "expired":
        listing.status = "expired"
        t = t + timedelta(hours=random.randint(20, 90))
        listing.logs.append(StatusLog(status="expired", changed_by_id=donor.id,
                                       note="Passed its best-by date unclaimed.", timestamp=t))
        listing.updated_at = t
        return listing

    if status_plan == "available":
        return listing

    recipient = random.choice(recipients)
    listing.recipient = recipient
    listing.status = "claimed"
    t = t + timedelta(hours=random.randint(1, 30))
    listing.logs.append(StatusLog(status="claimed", changed_by_id=recipient.id,
                                   note=f"Claimed by {recipient.name}.", timestamp=t))
    listing.updated_at = t

    if status_plan == "claimed":
        return listing

    if status_plan == "cancelled":
        t = t + timedelta(hours=random.randint(1, 10))
        listing.status = "cancelled"
        listing.logs.append(StatusLog(status="cancelled", changed_by_id=donor.id,
                                       note="Cancelled by donor.", timestamp=t))
        listing.updated_at = t
        return listing

    use_volunteer = status_plan in ("in_transit",) or (status_plan == "delivered" and random.random() < 0.6)

    if use_volunteer:
        volunteer = random.choice(volunteers)
        listing.volunteer = volunteer
        listing.status = "in_transit"
        t = t + timedelta(hours=random.randint(1, 12))
        listing.logs.append(StatusLog(status="in_transit", changed_by_id=volunteer.id,
                                       note=f"Pickup accepted by volunteer {volunteer.name}.", timestamp=t))
        listing.updated_at = t

        if status_plan == "in_transit":
            return listing

        t = t + timedelta(hours=random.randint(1, 8))
        listing.status = "delivered"
        listing.logs.append(StatusLog(status="delivered", changed_by_id=volunteer.id,
                                       note="Marked as delivered.", timestamp=t))
        listing.updated_at = t
        return listing

    # delivered directly by the recipient, no volunteer involved
    t = t + timedelta(hours=random.randint(1, 10))
    listing.status = "delivered"
    listing.logs.append(StatusLog(status="delivered", changed_by_id=recipient.id,
                                   note="Marked as delivered.", timestamp=t))
    listing.updated_at = t
    return listing


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        donors, recipients, volunteers = make_users()

        plan = (
            ["available"] * 120
            + ["claimed"] * 40
            + ["in_transit"] * 20
            + ["delivered"] * 30
            + ["cancelled"] * 6
            + ["expired"] * 4
        )
        random.shuffle(plan)
        now = datetime.utcnow()

        for status_plan in plan:
            donor = random.choice(donors)
            build_listing(donor, status_plan, recipients, volunteers, now)

        db.session.commit()

        total = Listing.query.count()
        print(f"Seeded {len(donors)} donors, {len(recipients)} recipients, "
              f"{len(volunteers)} volunteers, and {total} listings.")
        print("All seeded accounts use the password: ReplateDemo123")
        print(f"Example donor login:     {donors[0].email}")
        print(f"Example recipient login: {recipients[0].email}")
        print(f"Example volunteer login: {volunteers[0].email}")


if __name__ == "__main__":
    seed()
