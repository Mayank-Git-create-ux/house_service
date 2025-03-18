from flask import send_file, render_template, request, redirect, url_for, flash, session,abort
from app import app
from models import db, User, Service, ServiceRequest, Review
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import date, datetime
import os

# decorator for auth_required
def auth_required(f):
    @wraps(f)
    def inner_func(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login to continue")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return inner_func


# decorator for admin_required
def admin_required(f):
    @wraps(f)
    def inner_func(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login to continue")
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user.role == 'admin':
            flash('You are not authorized to access this page')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return inner_func


# Common routes---------------------------------------------------------------------->
@app.route('/')
def index():
    if 'user_id' not in session:
        services = Service.query.all()
        return render_template('index.html', services=services)

    user = User.query.get(session['user_id'])

    if not user:
        # User not found, handle accordingly
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role=='admin':
        return redirect(url_for('admin'))
    elif user.role=='customer':
        services=Service.query.all()
        users=User.query.all()
        service_requests=ServiceRequest.query.filter_by(customer_id=session['user_id'])
        return render_template('index.html', user=user, services=services, users=users, service_requests=service_requests)
    elif user.role=='professional':
        users=User.query.all()
        reviews=Review.query.all()
        service_requests = ServiceRequest.query.filter_by(professional_id=session['user_id']).all()
        services = [Service.query.get(sr.service_id) for sr in service_requests]
        total_base_price = sum(
        Service.query.get(sr.service_id).base_price 
        for sr in ServiceRequest.query.filter_by(professional_id=session['user_id'], status='closed').all()
        )
        return render_template('users/index_pro.html',total_base_price=total_base_price, user=user,reviews=reviews,services=services, users=users,service_requests=service_requests)
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first()
    
    if not user:
        flash("Invalid email id")
        return redirect(url_for('login'))
    
    if not check_password_hash(user.password_hash, password):
        flash("Invalid password")
        return redirect(url_for('login'))
    
    # Login successful, create session or token
    session['user_id'] = user.id

    flash('Login successfully')
    return redirect(url_for('index'))

@app.route('/logout')
@auth_required
def logout():
    session.pop('user_id')
    return redirect(url_for('login'))

@app.route('/pay/<int:id>')
@auth_required
def pay(id):
    service_request = ServiceRequest.query.get(id)
    if service_request.status != 'done':
        flash('Service request is not done yet!', 'error')
        return redirect(url_for('service_history'))
    
    user = User.query.get(session['user_id'])
    professional = User.query.get(service_request.professional_id)
    service = Service.query.get(service_request.service_id)
    
    # Calculate price
    if professional.experience:
        price = service.base_price + (professional.experience * 50)
    else:
        price = service.base_price
    
    return render_template('pay.html', user=user, professional=professional, service_request=service_request, service=service, price=price)

@app.route('/pay/<int:id>', methods=['POST'])
@auth_required
def pay_post(id):
    service_request = ServiceRequest.query.get(id)
    if service_request:
        # Update service request status to 'paid'
        service_request.status = 'paid'
        db.session.commit()
        flash('Payment successful!', 'success')
        return redirect(url_for('close_service', service_request_id=service_request.id))
    else:
        flash('Service request not found!', 'error')
        return redirect(url_for('pay', id=id))



# Customer routes--------------------------------------------------------------------->

@app.route('/register/customer')
def register_customer():
    return render_template('users/customer_register.html')

@app.route('/register/customer', methods=['POST'])
def register_customer_post():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    name = request.form.get('name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    pincode = request.form.get('pincode')
    
    if not username or not email or not password or not confirm_password or not name or not address or not phone or not pincode:
        flash('Please fill out al fields.')
        return redirect(url_for('register_costomer'))
    
    if password != confirm_password:
        flash('Passwords do not match')
        return redirect(url_for('register_costomer'))
    
    user = User.query.filter((User.username==username) | (User.email == email)).first()

    if user:
        if user.username == username:
            flash('Username already exists')
        elif user.email == email:
            flash('Email already exists')
        return redirect(url_for('register_costomer'))
    
    password_hash = generate_password_hash(password)

    new_user = User(username=username, email=email, password_hash=password_hash, name=name, address=address, phone=phone, pincode=pincode, role='customer')
    db.session.add(new_user)
    db.session.commit()

    flash('Register as costomer successfuly')
    return redirect(url_for('login'))

@app.route('/profile/customer')
@auth_required
def profile_cus():
    user = User.query.get(session['user_id'])
    return render_template('users/profile_customer.html', user=user)

@app.route('/profile/customer', methods=['POST'])
@auth_required
def profile_cus_post():
    username = request.form.get('username')
    email = request.form.get('email')
    c_password = request.form.get('c_password')
    password = request.form.get('password')
    name = request.form.get('name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    pincode = request.form.get('pincode')
    
    if not username or not email or not password or not c_password or not name or not address or not phone or not pincode:
        flash('Please fill out al fields.')
        return redirect(url_for('profile_cus'))
    
    user = User.query.get(session['user_id'])

    if not check_password_hash(user.password_hash, c_password):
        flash('Incorrect password')
        return redirect(url_for('profile_cus'))
    

    if user.username != username:
        new_username = User.query.filter_by(username=username).first()
        new_email = User.query.filter_by(email=email).first()
        if new_username:
            flash('Username already exists')
            return redirect(url_for('profile_cus'))
        if new_email:
            flash('Email already exists')
            return redirect(url_for('profile_cus'))
    
    new_password_hash = generate_password_hash(password)

    user.username=username 
    user.email=email 
    user.password_hash=new_password_hash 
    user.name=name 
    user.address=address
    user.phone=phone
    user.pincode=pincode

    db.session.commit()
    
    flash('Profile updated successfully')
    return redirect(url_for('profile_cus'))

@app.route('/show/<int:id>')
def show_service_to_user(id):
    users = User.query.all()
    service = Service.query.get(id)
    services = Service.query.all()
    
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        professionals = User.query.filter_by(service_name=service.name, status='approved').all()
        return render_template('show.html', 
                               user=user, 
                               service=service, 
                               users=users, 
                               services=services, 
                               professionals=professionals)
    else:
        return render_template('show.html', 
                               service=service, 
                               services=services, 
                               users=users)
@app.route('/book/<int:s_id>/<int:p_id>', methods=['GET', 'POST'])
@auth_required
def book_post(s_id, p_id):
    user=User.query.get(session['user_id'])

    new_service_request = ServiceRequest(customer_id=user.id, professional_id=p_id, service_id=s_id)
    db.session.add(new_service_request)
    db.session.commit()
    flash('booking successfull')
    return redirect(url_for('index'))

@app.route('/close_service/<int:id>', methods=['GET', 'POST'])
@auth_required
def close_service(id):
    user = User.query.get(session['user_id'])
    users = User.query.all()
    service_request = ServiceRequest.query.get(id)
    service = Service.query.get(service_request.service_id)

    if request.method == 'POST':
        rating = request.form.get('rating')
        remark = request.form.get('remark')

        # Save rating and remark to database
        service_request.rating = rating
        service_request.status = 'closed'
        service_request.date_of_completion = date.today()
        new_remark=Review(service_request_id=id, rating=rating, comments=remark)
        db.session.add(new_remark)
        db.session.commit()
        flash('Service closed successfully')
        return redirect(url_for('index'))
    
    return render_template('users/service_remark.html', user=user, users=users, service_request=service_request, service=service , date=date)

@app.route('/search_cus', methods=['GET'])
@auth_required
def search_customer():
    user = User.query.get(session['user_id'])

    parameter = request.args.get('parameter')
    query = request.args.get('query')

    if parameter == 'service_name':
        services = Service.query.filter(Service.name.ilike(f'%{query}%')).all()
        users = User.query.all()
        return render_template('users/search_cus.html', user=user, services=services, users=users, parameter=parameter, query=query)
    
    elif parameter == 'pin_code':
        users = User.query.filter(User.pincode.ilike(f'{query}')).all()
        services = Service.query.all()
        return render_template('users/search_cus.html', user=user, services=services, users=users, parameter=parameter, query=query)

    elif parameter == 'price' and query :
        query = float(query)
        services = Service.query.all()
        users = User.query.all()
        return render_template('users/search_cus.html', user=user, services=services, users=users, query=query, parameter=parameter)
    
    else:
        services = Service.query.all()
        return render_template('users/search_cus.html', user=user)
@app.route('/summary_cus')
@auth_required
def summary_customer():
    user = User.query.get(session['user_id'])
    
    ratings = ['1','2','3','4','5']
    statuses = ['requested','closed', 'assigned']
    
    # Filter ratings and status sizes by professional ID
    ratings_size = [Review.query.join(ServiceRequest).filter(ServiceRequest.customer_id == session['user_id'], Review.rating == rating).count() for rating in ratings]
    service_request_status_sizes = [ServiceRequest.query.filter_by(customer_id=session['user_id'], status=status).count() for status in statuses]
    
    return render_template('users/summary_cus.html', user=user, ratings_size=ratings_size, service_request_status_sizes=service_request_status_sizes)

@app.route('/history')
@auth_required
def history_customer():
    users = User.query.all()
    services = Service.query.all()
    user = User.query.get(session['user_id'])
    service_requests = ServiceRequest.query.filter_by(customer_id=session['user_id']).order_by(ServiceRequest.id.desc())
    return render_template('history_cus.html', user=user, services=services, users=users, service_requests=service_requests)
@app.route('/cancel_service/<id>')
@auth_required
def cancel_service(id):
    service_request = ServiceRequest.query.get(id)
    if service_request and service_request.customer_id == session['user_id']:
        service_request.status = 'cancelled'
        db.session.commit()
        flash('Service request cancelled successfully', 'success')
    else:
        flash('Invalid service request', 'error')
    return redirect(url_for('history_customer'))



# Professional routes----------------------------------------------------------------->

@app.route('/register/professional')
def register_professional():
    service=Service.query.all()
    return render_template('users/professional_register.html',service=service)

@app.route('/register/professional', methods=['POST'])
def register_professional_post():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    name = request.form.get('name')
    service_name  = request.form.get('service_name')
    service_description = request.form.get('service_description')
    experience = request.form.get('experience')
    file = request.files['file']
    address = request.form.get('address')
    phone = request.form.get('phone')
    pincode = request.form.get('pincode')
    
    if not username or not email or not password or not confirm_password or not name or not service_name or not service_description or not experience or not address or not phone or not pincode:
        flash('Please fill out al fields.')
        return redirect(url_for('register_professional'))
    
    if password != confirm_password:
        flash('Password do not match')
        return redirect(url_for('register_professional'))
    
    user = User.query.filter((User.username==username) | (User.email == email)).first()

    if user:
        if user.username == username:
            flash('Username already exists')
        elif user.email == email:
            flash('Email already exists')
        return redirect(url_for('register_professional'))
    
    if file:
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/files')
    
        # Create the upload folder if it doesn't exist
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
    
        file.save(os.path.join(upload_folder, filename))
    
    password_hash = generate_password_hash(password)
    

    new_user = User(username=username, email=email, password_hash=password_hash, name=name,service_name=service_name, service_description=service_description, experience=experience, document=filename, address=address,phone=phone, pincode=pincode, role='professional')
    db.session.add(new_user)
    db.session.commit()

    flash('Register as professional successfully')
    return redirect(url_for('login'))

@app.route('/profile/professional')
@auth_required
def profile_pro():
    user = User.query.get(session['user_id'])
    service = Service.query.all()
    return render_template('users/profile_professional.html', user=user, service=service)

@app.route('/profile/professional', methods=['POST'])
@auth_required
def profile_pro_post():
    username = request.form.get('username')
    email = request.form.get('email')
    c_password = request.form.get('c_password')
    password = request.form.get('password')
    name = request.form.get('name')
    service_name = request.form.get('service_name')
    service_description = request.form.get('service_description')
    experience = request.form.get('experience')
    file = request.files['file']
    address = request.form.get('address')
    phone = request.form.get('phone')
    pincode = request.form.get('pincode')
    
    if not username or not email or not password or not c_password or not name or not service_name or not experience or not address or not pincode:
        flash('Please fill out all fields.')
        return redirect(url_for('profile_pro'))
    
    user = User.query.get(session['user_id'])

    if not check_password_hash(user.password_hash, c_password):
        flash('Incorrect password')
        return redirect(url_for('profile_pro'))
    
    if user.username != username:
        new_username = User.query.filter_by(username=username).first()
        new_email = User.query.filter_by(email=email).first()
        if new_username:
            flash('Username already exists')
            return redirect(url_for('profile_pro'))
        if new_email:
            flash('Email already exists')
            return redirect(url_for('profile_pro'))
    
    # Ensure UPLOAD_FOLDER is defined
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/files', filename))
        user.document = filename
    
    new_password_hash = generate_password_hash(password)

    user.username=username 
    user.email=email 
    user.password_hash=new_password_hash 
    user.name=name 
    user.service_name=service_name
    user.service_description=service_description
    user.experience=experience 
    user.address=address
    user.phone=phone 
    user.pincode=pincode 

    db.session.commit()

    flash('Profile updated successfully')
    return redirect(url_for('profile_pro'))

@app.route('/accept_request/<int:id>', methods=['GET','POST'])
@auth_required
def accept_request(id):
    service_request=ServiceRequest.query.get(id)
    service_request.status='assigned'
    db.session.commit()
    flash('Service request accepted successfully')
    return redirect(url_for('index'))

@app.route('/mark_as_done/<int:id>', methods=['GET','POST'])
@auth_required
def mark_as_done(id):
    service_request=ServiceRequest.query.get(id)
    service_request.status='done'
    db.session.commit()
    flash('Service request marked as done successfully')
    return redirect(url_for('index'))

@app.route('/reject_request/<int:id>', methods=['GET','POST'])
@auth_required
def reject_request(id):
    service_request=ServiceRequest.query.get(id)
    service_request.status='rejected'
    db.session.commit()
    flash('Service request rejected')
    return redirect(url_for('index'))

@app.route('/serach_pro')
@auth_required
def search_professional():
    user=User.query.get(session['user_id'])
    reviews=Review.query.all()

    parameter = request.args.get('parameter')
    query = request.args.get('query')

    parameters = {
        'date': 'Date',
        'pin_code': 'Pin Code',
        'location': 'Location'
    }
    if parameter == 'date':
        from sqlalchemy import func
        try:
            date_query = datetime.strptime(query, '%d/%m/%y').date()
            service_requests = ServiceRequest.query.filter(
                func.date(ServiceRequest.date_of_request) == date_query
            ).all()
            users = User.query.all()
            return render_template('users/search_pro.html', parameters=parameters, param=parameter, query=query, user=user, service_requests=service_requests, users=users, reviews=reviews)
        except ValueError:
            # Handle invalid date format
            return render_template('users/search_pro.html', error='Invalid date format', parameters=parameters, param=parameter, query=query, user=user)
        
    if parameter == 'pin_code':
        users = User.query.filter_by(role='customer').filter(User.pincode.ilike(f'{query}')).all()
        service_requests=ServiceRequest.query.all()
        return render_template('users/search_pro.html',parameters=parameters, param=parameter, query=query, user=user, service_requests=service_requests, users=users, reviews=reviews)

    if parameter == 'location':
        service_requests=ServiceRequest.query.all()
        users = User.query.filter_by(role='customer').filter(User.address.ilike(f'%{query}%')).all()
        return render_template('users/search_pro.html',parameters=parameters, param=parameter,query=query, user=user, service_requests=service_requests, users=users, reviews=reviews)    
    
    return render_template('users/search_pro.html', user=user,parameters=parameters, param=parameter,query=query)

@app.route('/summary_pro')
@auth_required
def summary_professional():
    user = User.query.get(session['user_id'])
    
    ratings = ['1','2','3','4','5']
    statuses = ['requested', 'assigned', 'closed', 'rejected']
    
    # Filter ratings and status sizes by professional ID
    ratings_size = [Review.query.join(ServiceRequest).filter(ServiceRequest.professional_id == session['user_id'], Review.rating == rating).count() for rating in ratings]
    service_request_status_sizes = [ServiceRequest.query.filter_by(professional_id=session['user_id'], status=status).count() for status in statuses]
    
    return render_template('users/summary_pro.html', user=user, ratings_size=ratings_size, service_request_status_sizes=service_request_status_sizes)



# Admin routes------------------------------------------------------------------------>

@app.route('/admin')
@admin_required
def admin():
    user=User.query.get(session['user_id'])
    services=Service.query.all()
    users=User.query.all()
    service_requests = ServiceRequest.query.order_by(ServiceRequest.id.desc()).all()
    return render_template('users/admin.html', user=user, services=services, users=users, service_requests=service_requests)

@app.route('/service/add')
@admin_required
def add_service():
    user = User.query.get(session['user_id'])
    return render_template('service/add.html',user=user)

@app.route('/service/add', methods=['POST'])
@admin_required
def add_service_post():
    name = request.form.get('name')
    description = request.form.get('description')
    base_price = request.form.get('base_price')
    url = request.form.get('url')

    if not name or not description or not base_price:
        flash('Please fil out all fields')
        return redirect(url_for('add_service'))
    
    service = Service(name=name, description=description, base_price=base_price, url=url)
    db.session.add(service)
    db.session.commit()

    flash('Service added successfully')
    return redirect(url_for('admin'))

@app.route('/service/<int:id>/')
@admin_required
def show_service(id):
    user=User.query.get(session['user_id'])
    service=Service.query.get(id)
    return render_template('service/show.html', user=user, service=service)

@app.route('/service/<int:id>/edit')
@admin_required
def edit_service(id):
    user=User.query.get(session['user_id'])
    service=Service.query.get(id)
    if not service:
        flash('Service does not exist')
        return redirect(url_for('admin'))
    return render_template('service/edit.html', user=user, service=service)

@app.route('/service/<int:id>/edit', methods=["POST"])
@admin_required
def edit_service_post(id):
    user=User.query.get(session['user_id'])
    service=Service.query.get(id)
    if not service:
        flash('Service does not exist')
        return redirect(url_for('admin'))
    
    name = request.form.get('name')
    description = request.form.get('description')
    base_price = request.form.get('base_price')
    url = request.form.get('url')

    if not name or not description or not base_price:
        flash('Please fil out all fields')
        return redirect(url_for('edit_service', id=id))
    
    
    service.name=name 
    service.description=description 
    service.base_price=base_price
    service.url=url
    db.session.commit()

    flash('Service updated successfully')
    return redirect(url_for('admin'))
    
@app.route('/service/<int:id>/delete')
@admin_required
def delete_service(id):
    user=User.query.get(session['user_id'])
    service=Service.query.get(id)
    if not service:
        flash('Service does not exist')
        return redirect(url_for('admin'))
    return render_template('service/delete.html', user=user, service=service)

@app.route('/service/<int:id>/delete', methods=['POST'])
@admin_required
def delete_service_post(id):
    user=User.query.get(session['user_id'])
    service=Service.query.get(id)
    if not service:
        flash('Service does not exist')
        return redirect(url_for('admin'))
    db.session.delete(service)
    db.session.commit()
    flash('Service deleted successfully')
    return redirect(url_for('admin'))

@app.route('/professional/<int:id>/')
@admin_required
def show_professional(id):
    user=User.query.get(session['user_id'])
    user_=User.query.get(id)
    return render_template('users/show.html', user=user, user_=user_)

@app.route('/approve/<int:id>',methods=['GET','POST'])
@admin_required
def approve(id):
    user=User.query.get(id)
    user.status='approved'
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/reject/<int:id>',methods=['GET','POST'])
@admin_required
def reject(id):
    user=User.query.get(id)
    user.status='rejected'
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_user/<int:id>', methods=['GET','POST'])
@admin_required
def delete_user(id):
    user = User.query.get(id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/serach_admin')
@admin_required
def search_admin():
    user=User.query.get(session['user_id'])
    users=User.query.all()

    parameter = request.args.get('parameter')
    query = request.args.get('query')

    parameters = {
        'service_request': 'Service Request',
        'services': 'Services',
        'professionals': 'Professionals'
    }
    if parameter == 'service_request':
        service_requests=ServiceRequest.query.filter(ServiceRequest.status.ilike(f'%{query}%')).all()
        users=User.query.all()
        return render_template('users/search_admin.html',parameters=parameters, param=parameter, query=query, user=user, service_requests=service_requests, users=users,)
    
    if parameter == 'services':
        services=Service.query.filter(Service.name.ilike(f'%{query}%')).all()
        users=User.query.all()
        return render_template('users/search_admin.html',parameters=parameters, param=parameter, query=query, user=user, services=services, users=users)
    
    if parameter == 'professionals':
        users=User.query.filter(User.name.ilike(f'%{query}%')).all()
        return render_template('users/search_admin.html',parameters=parameters, param=parameter, query=query, user=user, users=users)
    
    
    return render_template('users/search_admin.html',parameters=parameters, param=parameter, query=query, user=user, users=users,)

@app.route('/summary_admin')
@admin_required
def summary_admin():
    user=User.query.get(session['user_id'])
    ratings = ['1','2','3','4','5']
    statuses = ['requested', 'assigned', 'closed']
    ratings_size = [Review.query.filter_by(rating=rating).count() for rating in ratings]
    service_request_status_sizes = [ServiceRequest.query.filter_by(status=status).count() for status in statuses]
    return render_template('users/summary_admin.html',user=user, ratings_size=ratings_size, service_request_status_sizes=service_request_status_sizes)

@app.route('/view_document/<int:id>')
def view_document(id):
    user = User.query.get(id)
    if user and user.document:
        file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/files', user.document)
        return send_file(file_path, mimetype='application/pdf')
    return abort(404)