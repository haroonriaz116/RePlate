# RePlate

A full-stack food redistribution platform that connects donors, recipients, and volunteers around surplus food before it expires. Built with Flask, SQLAlchemy, and server-rendered HTML/CSS templates.

## What it does

Donors post a listing describing surplus food, its quantity, a best-by date, and a pickup location. Recipients browse open listings and claim what they need. If a recipient cannot get there themselves, a volunteer can accept the delivery run. Every change in a listing's status (posted, claimed, in transit, delivered, cancelled, expired) is written to an append-only status log, so the full history of a donation is auditable rather than resting on a single mutable field.

The database is seeded with 220 listings across every status and category, plus a roster of donor, recipient, and volunteer accounts, to demonstrate the platform running at the scale described on the resume bullet (200+ active listings). Listing queries are indexed on status, category, expiry date, and the foreign keys joining listings to users, and the browse page is paginated, so performance holds up as the table grows well past 220 rows.

## Project structure

```
replate/
├── app.py            # application factory, blueprint registration, Jinja filters
├── config.py         # configuration (secret key, database URI)
├── extensions.py     # shared SQLAlchemy / Flask-Login instances
├── models.py         # User, Listing, StatusLog
├── main.py           # home page blueprint
├── auth.py           # register / login / logout blueprint
├── listings.py       # browse, detail, create, and status-transition routes
├── dashboard.py      # role-specific dashboards (donor / recipient / volunteer)
├── seed.py           # populates the database with demo data
├── templates/        # Jinja templates
├── static/css/       # stylesheet
├── requirements.txt
└── replate.db        # pre-seeded SQLite database
```

## Getting started

### Prerequisites

* Python 3.x

### Installation

```
git clone https://github.com/your-username/replate.git
cd replate
python3 -m venv venv
source venv/bin/activate      # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Running it

A pre-seeded replate.db ships with the project, so this is enough to see a populated platform:

```
python app.py
```

The app runs at http://127.0.0.1:5000.

To wipe the database and generate a fresh set of demo data instead:

```
python seed.py
python app.py
```

## Demo logins

All seeded accounts share the password ReplateDemo123. A few examples:

| Role | Email |
| --- | --- |
| Donor | maple.street.bakery@replate.demo |
| Recipient | hopewell.shelter@replate.demo |
| Volunteer | printed to the console after running seed.py |

You can also sign up for a new account from the home page. The role you pick determines what the dashboard and listing actions look like.

## Data model

* User — covers all three roles (donor, recipient, volunteer) through a single role column rather than separate tables, since the roles share the same fields.
* Listing — one food donation post, from creation through pickup, with status, category, quantity, expiry date, and pickup details.
* StatusLog — an append-only record of every status change a listing goes through, so donation history is auditable rather than overwritten.

## Design notes

The brand mark is a plate with a fork and knife inside a gradient badge, used in the navbar and as a large translucent watermark behind the hero. The interface follows a clean, light system: a soft mint background, white rounded cards with gentle shadows, an emerald-to-coral palette, pill-shaped buttons and status badges, and category emoji on each listing card for a quick visual read while scanning a long list. Sora carries the headlines and Inter carries the body text and UI copy.

## License

This project is licensed under the MIT License.

## Contact

Haroon Riaz — haroonriaz116@gmail.com
