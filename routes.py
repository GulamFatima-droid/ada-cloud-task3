# routes.py
from flask import render_template, url_for, flash, redirect, request
from app import app, db, logger
from models import User, Job # Import User and Job models
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

@app.route("/")
@app.route("/home")
def home():
    """
    Home page route. Displays all jobs.
    """
    jobs = Job.query.order_by(Job.date_posted.desc()).all()

    if not jobs:
        logger.info("No jobs found in the database.")

    for job in jobs:
        job.formatted_date = job.date_posted.strftime('%Y-%m-%d')

    return render_template('index.html', jobs=jobs)

@app.route("/register", methods=['GET', 'POST'])
def register():
    """
    User registration route.
    Handles both displaying the registration form (GET) and processing form submission (POST).
    """
    # If the user is already logged in, redirect to home page
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Basic validation
        if not username or not email or not password or not confirm_password:
            flash('All fields are required!', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')

        # Check if username or email already exists
        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()

        if user_exists:
            flash('Username already taken. Please choose a different one.', 'danger')
            return render_template('register.html')
        if email_exists:
            flash('Email already registered. Please use a different email or login.', 'danger')
            return render_template('register.html')

        # Create new user and add to database
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password_hash=hashed_password)
        try:
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You are now able to log in.', 'success')
            logger.info(f"New user registered: {username}")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during registration: {e}', 'danger')
            logger.error(f"Error during registration: {e}")
            print(f"Error during registration: {e}") # Log the error for debugging
            return render_template('register.html')

    return render_template('register.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    """
    User login route.
    Handles both displaying the login form (GET) and processing form submission (POST).
    """
    # If the user is already logged in, redirect to home page
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            # Redirect to the page the user was trying to access before logging in, or home
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            logger.info(f"User {user.username} logged in successfully.")
            return redirect(next_page or url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            logger.warning(f"Failed login attempt for email: {email}")

    return render_template('login.html')

@app.route("/logout")
@login_required # Requires user to be logged in to access this route
def logout():
    """
    User logout route.
    Logs out the current user and redirects to the home page.
    """
    logout_user()
    flash('You have been logged out.', 'info')
    logger.info(f"User {current_user.username} logged out successfully.")
    return redirect(url_for('home'))

@app.route("/job/new", methods=['GET', 'POST'])
@login_required # Requires user to be logged in to create a job
def new_job():
    """
    Route for creating a new job.
    Handles both displaying the job creation form (GET) and processing form submission (POST).
    """
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')

        if not title or not description:
            flash('Title and Description are required for the job.', 'danger')
            return render_template('create_job.html', title='New Job')

        # Create a new Job instance linked to the current logged-in user
        job = Job(title=title, description=description, author=current_user)
        try:
            db.session.add(job)
            db.session.commit()
            flash('Your job has been created!', 'success')
            logger.info(f"New job created: {job.title} by {current_user.username}")
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while creating the job: {e}', 'danger')
            print(f"Error creating job: {e}")
            logger.error(f"Error creating job: {e}")
            return render_template('create_job.html', title='New Job')

    return render_template('create_job.html', title='New Job')

@app.route("/job/<int:job_id>")
def job_detail(job_id):
    """
    Route to view details of a specific job.
    """
    job = Job.query.get_or_404(job_id)
    return render_template('job_detail.html', title=job.title, job=job)

@app.route("/job/<int:job_id>/update", methods=['GET', 'POST'])
@login_required
def update_job(job_id):
    """
    Route to update an existing job.
    Only the author of the job can update it.
    """
    job = Job.query.get_or_404(job_id)
    # Ensure only the author can update their job
    if job.author != current_user:
        flash('You are not authorised to update this job.', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        job.title = request.form.get('title')
        job.description = request.form.get('description')
        job.is_completed = True if request.form.get('is_completed') == 'on' else False

        if not job.title or not job.description:
            flash('Title and Description are required for the job.', 'danger')
            return render_template('create_job.html', title='Update Job', job=job)

        try:
            db.session.commit()
            flash('Your job has been updated!', 'success')
            logger.info(f"Job updated: {job.title} by {current_user.username}")
            return redirect(url_for('job_detail', job_id=job.id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating the job: {e}', 'danger')
            print(f"Error updating job: {e}")
            logger.error(f"Error updating job: {e}")
            return render_template('create_job.html', title='Update Job', job=job)

    return render_template('create_job.html', title='Update Job', job=job)

@app.route("/job/<int:job_id>/delete", methods=['POST'])
@login_required
def delete_job(job_id):
    """
    Route to delete an existing job.
    Only the author of the job can delete it.
    """
    job = Job.query.get_or_404(job_id)
    # Ensure only the author can delete their job
    if job.author != current_user:
        flash('You are not authorised to delete this job.', 'danger')
        return redirect(url_for('home'))

    try:
        db.session.delete(job)
        db.session.commit()
        flash('Your job has been deleted!', 'success')
        logger.info(f"Job deleted: {job.title} by {current_user.username}")
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the job: {e}', 'danger')
        print(f"Error deleting job: {e}")
        logger.error(f"Error deleting job: {e}")
        return redirect(url_for('job_detail', job_id=job.id))

