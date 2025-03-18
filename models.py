from app import app
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.Integer)
    pincode = db.Column(db.Integer, nullable=True)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'customer', 'professional'
    status = db.Column(db.String(20), default='approved') # 'approved', 'rejected', 

    # Customer-specific fields
    service_name = db.Column(db.String(100), nullable=True)
    service_description = db.Column(db.Text)
    experience = db.Column(db.Integer, nullable=True)
    document = db.Column(db.String(100), nullable=True)  # store file name or path


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    base_price = db.Column(db.Float, nullable=False)
    url = db.Column(db.Text) # Time in minutes


class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    date_of_request = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='requested') # 'requested', 'assigned', 'closed'
    date_of_completion = db.Column(db.DateTime)


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey('service_requests.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1 to 5
    comments= db.Column(db.Text)


with app.app_context():
    db.create_all()
    # if admin exists, else create admin
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        password_hash = generate_password_hash('admin')
        admin = User(username='admin', email='admin@gmail.com',password_hash=password_hash, name='Admin_User', role='admin')
        db.session.add(admin)
        db.session.commit()