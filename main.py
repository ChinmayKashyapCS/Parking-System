import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort,send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.orm import aliased
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from flask_migrate import Migrate

curr_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///serviceapp.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.secret_key = "letsencrypt"
app.config['PASSWORD_HASH'] = 'sha512'

app.config['UPLOAD_EXTENSIONS'] = ['.pdf']
app.config['UPLOAD_PATH'] = os.path.join(curr_dir, 'static', "pdfs")

db = SQLAlchemy()

db.init_app(app)
app.app_context().push()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('customer', lazy=True))
    had_booked = db.Column(db.Boolean, default=False)

class Contractor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('contractor', lazy=True))
    mall_name = db.Column(db.String(120))
    city = db.Column(db.String(100))
    number_of_lots = db.Column(db.Integer)
    prize = db.Column(db.Integer)


class AlternativeContractor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('alternative_contractor', lazy=True))
    mall_name = db.Column(db.String(120))
    city = db.Column(db.String(100))
    number_of_lots = db.Column(db.Integer)
    prize = db.Column(db.Integer)
    is_near_mall = db.Column(db.Boolean, default=False) 
    is_near_busy_street = db.Column(db.Boolean, default=False) 
    street_name = db.Column(db.String(120))  
    distance_from_mall = db.Column(db.Float) 
    distance_from_street = db.Column(db.Float)



class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    contractor_id = db.Column(db.Integer, db.ForeignKey('contractor.id'), nullable=False)
    mall_name = db.Column(db.String(120))
    city = db.Column(db.String(100))
    slot_no = db.Column(db.Integer)
    prize = db.Column(db.Integer)


    customer = db.relationship('Customer', backref=db.backref('bookings', lazy=True))
    contractor = db.relationship('Contractor', backref=db.backref('bookings', lazy=True))

class ApprovalStatus(db.Model):
    __tablename__ = 'approval_status'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('approval_status', lazy=True))

def create_admin_user():

    existing_admin = User.query.filter_by(username='admin').first()

    if existing_admin:

        print("Admin user already exists.")
        return


    hashed_password = generate_password_hash('1234')
    new_admin = User(username='admin', email='admin@example.com', 
                     password=hashed_password, phone='1234567890', 
                     address='Admin Address', role='admin')

    db.session.add(new_admin)
    db.session.commit()

    print("Admin user created successfully.")

@app.route('/')
def index():
    create_admin_user()
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Fetch user from the database
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):  # Verify the password
            session['user_id'] = user.id  # Store user ID in the session
            session['role'] = user.role   # Store the user role in the session

            # Redirect based on role
            if user.role == 'customer':
                return redirect(url_for('customer_dashboard'))
            elif user.role == 'contractor':
                return redirect(url_for('contractor_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid user role.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout(): 
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login')) 

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin_user = User.query.filter_by(username='admin', role='admin').first()

        if admin_user and check_password_hash(admin_user.password, password):

            session['admin_logged_in'] = True
            session['admin_id'] = admin_user.id
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password!', 'danger')

    return render_template('admin_login.html')


@app.route('/signup_customer', methods=['GET', 'POST'])
def signup_customer():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        address = request.form['address']

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('User already exists, please try again with a different email address.', 'warning')
            return redirect(url_for('signup_customer'))

        # Hash the password before storing
        hashed_password = generate_password_hash(password)

        # Create a new user record
        new_user = User(username=username, email=email, password=hashed_password, phone=phone, address=address, role='customer')
        db.session.add(new_user)
        db.session.commit()

        # Create a new customer record
        new_customer = Customer(user_id=new_user.id)
        db.session.add(new_customer)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template("signup_customer.html")

@app.route('/signup_contractor', methods=['GET', 'POST'])
def signup_contractor():
    # Dictionary mapping cities to malls
    city_malls = {
        "Bengaluru (Bangalore)": [
            "Phoenix Marketcity", "Orion Mall", "UB City", "Mantri Square Mall",
            "Garuda Mall", "Forum Mall Koramangala", "Inorbit Mall", "Forum Shantiniketan Mall",
            "Royal Meenakshi Mall", "Park Square Mall", "Bangalore Central Mall", "Elements Mall",
            "Gopalan Innovation Mall", "Esteem Mall", "Total Mall"
        ],
        "Mysuru (Mysore)": ["Mall of Mysore", "Forum Centre City Mall"],
        "Mangaluru (Mangalore)": ["Forum Fiza Mall", "City Centre Mall", "Bharath Mall"],
        "Hubballi-Dharwad": ["Urban Oasis Mall", "Laxmi Mall"],
        "Belagavi (Belgaum)": ["Nucleus Mall", "Reliance Mall"],
        "Kalaburagi (Gulbarga)": ["Asian Mall", "Sun Centre Mall"],
        "Ballari (Bellary)": ["Bellary Central Mall"],
        "Udupi": ["City Centre Mall"],
        "Davangere": ["BSC City Centre Mall"],
        "Tumakuru (Tumkur)": ["SS Mall"]
    }

    # Retrieve the selected city from the form
    selected_city = request.form.get('city') if request.method == 'POST' else None
    malls = city_malls.get(selected_city, []) if selected_city else []

    if request.method == 'POST' and 'submit_signup' in request.form:
        # Extract form data
        username = request.form['username']
        email = request.form['email']
        raw_password = request.form['password']  # Raw password before hashing
        phone = request.form['phone']
        address = request.form['address']
        mall_name = request.form['mall_name']
        city = request.form['city']
        number_of_lots = request.form['number_of_lots']
        prize = request.form['prize']

        # Hash the password
        hashed_password = generate_password_hash(raw_password)

        # Validate email uniqueness
        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'danger')
            return redirect(url_for('signup_contractor'))

        try:
            # Create and save the user
            user = User(username=username, email=email, password=hashed_password, phone=phone, address=address, role='contractor')
            db.session.add(user)
            db.session.flush()  # Ensure user ID is generated for the foreign key

            # Create and save the contractor
            contractor = Contractor(user_id=user.id, mall_name=mall_name, city=city, number_of_lots=number_of_lots, prize=prize)
            db.session.add(contractor)

            # Create and save the approval status
            approval_status = ApprovalStatus(user_id=user.id, username=username, role='contractor', is_approved=False)
            db.session.add(approval_status)

            # Commit all changes
            db.session.commit()

            flash('Contractor signup successful! Awaiting approval.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            # Rollback in case of error
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('signup_contractor'))

    # Render the signup form
    return render_template('signup_contractor.html', city_malls=city_malls, selected_city=selected_city, malls=malls)



@app.route('/signup_alternative_contractor', methods=['GET', 'POST'])
def signup_alternative_contractor():
    malls = {
        'Bengaluru': [
            'Phoenix Marketcity', 'Orion Mall', 'UB City', 'Mantri Square Mall', 'Garuda Mall',
            'Forum Mall Koramangala', 'Inorbit Mall', 'Forum Shantiniketan Mall', 'Royal Meenakshi Mall',
            'Park Square Mall', 'Bangalore Central Mall', 'Elements Mall', 'Gopalan Innovation Mall',
            'Esteem Mall', 'Total Mall'
        ],
        'Mysuru': ['Mall of Mysore', 'Forum Centre City Mall'],
        'Mangaluru': ['Forum Fiza Mall', 'City Centre Mall', 'Bharath Mall'],
        'Hubballi-Dharwad': ['Urban Oasis Mall', 'Laxmi Mall'],
        'Belagavi': ['Nucleus Mall', 'Reliance Mall'],
        'Kalaburagi': ['Asian Mall', 'Sun Centre Mall'],
        'Ballari': ['Bellary Central Mall'],
        'Udupi': ['City Centre Mall'],
        'Davangere': ['BSC City Centre Mall'],
        'Tumakuru': ['SS Mall']
    }

    busy_streets = {
        'Bengaluru': [
            'Commercial Street', 'Brigade Road', 'Church Street', 'Mosque Road', 'Malleswaram 8th Cross',
            'KR Market (City Market)', 'Avenue Road', 'Chickpet', 'Majestic Area (Gandhinagar)',
            'Indiranagar 100 Feet Road', 'Koramangala 5th Block', 'JP Nagar Central Market',
            'Jayanagar 4th Block Complex', 'HSR Layout Sector 1 Market', 'Whitefield ITPL Road',
            'Rajajinagar (Orion Mall Vicinity)', 'Marathahalli Outer Ring Road', 'Shivajinagar Market'
        ],
        'Mysuru': ['Devaraja Market Area'],
        'Mangaluru': ['Hampankatta'],
        'Hubballi-Dharwad': ['Durgadbail'],
        'Belagavi': ['Khade Bazaar'],
        'Kalaburagi': ['Super Market Area'],
        'Ballari': ['Cowl Bazaar'],
        'Udupi': ['Car Street'],
        'Davangere': ['Bada Bazaar'],
        'Tumakuru': ['Market Road']
    }

    if request.method == 'POST':
        # Basic details
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        address = request.form['address']
        city = request.form['city']
        near_to = request.form['near_to']

        # Mall-specific details
        mall_name = request.form.get('mall_name')
        distance_from_mall = request.form.get('distance_from_mall')

        # Busy-street-specific details
        street_name = request.form.get('street_name')
        distance_from_street = request.form.get('distance_from_street')

        number_of_lots = request.form['number_of_lots']
        prize = request.form['prize']
        is_near_mall = near_to == 'mall'
        is_near_busy_street = near_to == 'busy_street'

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'danger')
            return redirect(url_for('signup_alternative_contractor'))

        # Save user
        user = User(username=username, email=email, password=password, phone=phone, address=address, role='alternative_contractor')
        db.session.add(user)
        db.session.commit()

        # Save alternative contractor
        contractor = AlternativeContractor(
            user_id=user.id, mall_name=mall_name, city=city, street_name=street_name,
            is_near_mall=is_near_mall, is_near_busy_street=is_near_busy_street,
            distance_from_mall=distance_from_mall, distance_from_street=distance_from_street,
            number_of_lots=number_of_lots, prize=prize
        )
        db.session.add(contractor)
        db.session.commit()

        # Save approval status
        approval_status = ApprovalStatus(user_id=user.id, username=username, role='alternative_contractor', is_approved=False)
        db.session.add(approval_status)
        db.session.commit()

        flash('Alternative Contractor signup successful! Awaiting approval.', 'success')
        return redirect(url_for('login'))

    return render_template('signup_alternative_contractor.html', malls=malls, busy_streets=busy_streets)

@app.route('/intermediate_page', methods=['GET'])
def intermediate_page():
    return render_template('intermediate_page.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    # Fetch users with pending approval
    unapproved_users = ApprovalStatus.query.filter_by(is_approved=False).all()
    approved_users = ApprovalStatus.query.filter_by(is_approved=True).all()

    # Fetch all bookings
    bookings = Booking.query.all()

    for approval_status in unapproved_users + approved_users:
        user = User.query.filter_by(id=approval_status.user_id).first_or_404()
        approval_status.user_details = user

        if user.role == 'contractor':
            user.contractor_details = Contractor.query.filter_by(user_id=user.id).first()
        elif user.role == 'alternative_contractor':
            user.alternative_contractor_details = AlternativeContractor.query.filter_by(user_id=user.id).first()

    if request.method == 'POST':
        user_id = request.form.get('user_id')  # Use `get` to avoid BadRequestKeyError

        if not user_id:
            # If user_id is not in the form data, return an error or handle it
            flash('User ID is missing', 'error')
            return redirect(url_for('admin_dashboard'))

        if 'approve_user' in request.form:
            # Approve user in ApprovalStatus
            approval_status = ApprovalStatus.query.filter_by(user_id=user_id).first_or_404()
            approval_status.is_approved = True
            db.session.commit()
            flash('User approved successfully', 'success')
            return redirect(url_for('admin_dashboard'))

        if 'reject_user' in request.form:
            # Reject user in ApprovalStatus
            approval_status = ApprovalStatus.query.filter_by(user_id=user_id).first_or_404()
            approval_status.is_approved = False
            db.session.commit()
            flash('User rejected successfully', 'error')
            return redirect(url_for('admin_dashboard'))

    return render_template('admin_dashboard.html', unapproved_users=unapproved_users, approved_users=approved_users, bookings=bookings,dashboard_name='admin')





@app.route('/customer_dashboard', methods=['GET', 'POST'])
def customer_dashboard():
    user_id = session.get('user_id')

    if not user_id:
        flash("Please log in to access the customer dashboard.", "warning")
        return redirect(url_for('login'))  # Redirect to login if user is not logged in

    # Fetch the customer based on user_id
    customer = Customer.query.filter_by(user_id=user_id).first()
    if not customer:
        flash("Customer not found.", "warning")
        return redirect(url_for('login'))

    # Fetching the customer's booking history
    bookings = Booking.query.filter_by(customer_id=customer.id).all()

    # Handling Parking Booking and Profile Update
    if request.method == 'POST':
        # Handle Parking Booking
        if 'book_parking' in request.form:
            city = request.form['city']
            mall_name = request.form['mall_name']
            street_name = request.form['street_name']  # This can still be used to query alternative contractors

            # Check if parking slots are available in Contractor or AlternativeContractor
            contractor = Contractor.query.filter_by(city=city, mall_name=mall_name).first()
            alternative_contractor = AlternativeContractor.query.filter_by(city=city, street_name=street_name).first()

            if contractor or alternative_contractor:
                # Determine the prize and update available slots
                if contractor and contractor.number_of_lots > 0:
                    prize = contractor.prize
                    contractor.number_of_lots -= 1  # Decrement available slots
                    db.session.commit()
                    contractor_id = contractor.id
                elif alternative_contractor and alternative_contractor.number_of_lots > 0:
                    prize = alternative_contractor.prize
                    alternative_contractor.number_of_lots -= 1  # Decrement available slots
                    db.session.commit()
                    contractor_id = alternative_contractor.id
                else:
                    flash('Parking slots not available!', 'error')
                    return redirect(url_for('customer_dashboard'))

                # Create the booking entry
                booking = Booking(
                    customer_id=customer.id,
                    contractor_id=contractor_id,
                    mall_name=mall_name,
                    city=city,
                    prize=prize
                )
                db.session.add(booking)
                db.session.commit()
                flash(f'Parking slot booked successfully! Prize: {prize}', 'success')
                return redirect(url_for('customer_dashboard'))

            flash('Parking slots not available!', 'error')
            return redirect(url_for('customer_dashboard'))

        # Handle Profile Update (via modal submission)
        if 'update_profile' in request.form:
            # Update the customer profile details
            user = customer.user  # Fetch the associated User object
            user.address = request.form['address']
            user.email = request.form['email']
            user.phone = request.form['phone']

            db.session.commit()
            flash("Your profile has been updated successfully!", "success")

            # Return updated customer data to update the modal without redirecting
            return jsonify({
                'address': user.address,
                'email': user.email,
                'phone': user.phone
            })

        # Handle the "Completed" button click
        if 'completed_booking' in request.form:
            booking_id = request.form['booking_id']
            booking = Booking.query.filter_by(id=booking_id).first_or_404()

            # Assuming completed means releasing the parking slot back
            contractor = Contractor.query.filter_by(id=booking.contractor_id).first()
            alternative_contractor = AlternativeContractor.query.filter_by(id=booking.contractor_id).first()

            if contractor:
                contractor.number_of_lots += 1  # Increment available slots
            elif alternative_contractor:
                alternative_contractor.number_of_lots += 1  # Increment available slots

            db.session.commit()
            flash('Booking marked as completed! Parking slot is now available.', 'success')

            return redirect(url_for('customer_dashboard'))

    return render_template('customer_dashboard.html', customer=customer, bookings=bookings, dashboard_name='customer')













@app.route('/contractor_dashboard', methods=['GET', 'POST'])
def contractor_dashboard():
    user_id = session.get('user_id')
    
    if not user_id:
        flash("Please log in to access the contractor dashboard.", "warning")
        return redirect(url_for('login'))  # Redirect to login if user is not logged in

    # Retrieve the contractor record associated with the logged-in user
    contractor = Contractor.query.filter_by(user_id=user_id).first()

    # Retrieve the approval status of the contractor from the ApprovalStatus table
    approval_status = ApprovalStatus.query.filter_by(user_id=user_id).first()

    # Check if the contractor exists and is approved
    if not contractor or not approval_status or not approval_status.is_approved:
        flash("Your contractor profile is not approved yet.", "warning")
        return render_template('contractor_dashboard.html', contractor=None, bookings=None,dashboard_name="contractor")

    # Retrieve the contractor's booking history
    bookings = Booking.query.filter_by(contractor_id=contractor.id).all()

    if request.method == 'POST':
        if 'edit_profile' in request.form:
            # Handle profile edit form submission
            contractor.mall_name = request.form['mall_name']
            contractor.city = request.form['city']
            contractor.number_of_lots = request.form['number_of_lots']
            contractor.prize = request.form['prize']
            db.session.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for('contractor_dashboard'))

        if 'add_parking_slots' in request.form:
            # Handle the adding of parking slots (number_of_lots)
            try:
                contractor.number_of_lots += int(request.form['new_parking_slots'])
                db.session.commit()
                flash(f"{request.form['new_parking_slots']} parking slots added successfully.", "success")
            except ValueError:
                flash("Invalid input for parking slots.", "danger")
            return redirect(url_for('contractor_dashboard'))

    return render_template('contractor_dashboard.html', contractor=contractor, bookings=bookings,dashboard_name="contractor")






if __name__ == "__main__":
    with app.app_context():
        create_admin_user()
        db.create_all() 
    app.run(debug=True)
