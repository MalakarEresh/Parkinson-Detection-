import os
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from sqlalchemy import func
from app import db
from app.models import User, Report
# IMPORTANT: We import the master prediction function
from app.ml_logic import get_combined_prediction
from app.email import send_email

bp = Blueprint('main', __name__)

# --- Decorator for Admin-only routes ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# === USER-FACING ROUTES
# =============================================================================

@bp.route('/')
@bp.route('/index')
def index():
    """Renders the public landing page."""
    return render_template('index.html', title='Home')

@bp.route('/dashboard')
@login_required
def dashboard():
    """Renders the main user dashboard, which displays past reports."""
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.timestamp.desc()).all()
    return render_template('dashboard.html', title='Dashboard', reports=reports)

# STAGE 1: Serves the symptom form and handles its submission.
@bp.route('/new_test', methods=['GET', 'POST'])
@login_required
def new_test():
    """On GET, displays the symptom form. On POST, validates and redirects to the audio test page."""
    if request.method == 'POST':
        # Now we can collect the data directly with the correct names
        symptom_args = {
            'tremor': request.form.get('tremor'),
            'stiffness': request.form.get('stiffness'),
            'walking_issue': request.form.get('walking_issue'), # <-- THIS IS THE FIX
            'age': request.form.get('age'),
            'gender': request.form.get('gender'),
            'other_symptoms': request.form.get('other_symptoms', '')
        }
        
        # The validation logic now works perfectly because the keys match the form names
        if not all(symptom_args.get(key) for key in ['age', 'gender', 'tremor', 'stiffness', 'walking_issue']):
             flash('Please complete all fields in the step before proceeding.', 'warning')
             return render_template('new_test.html', title='New Test - Step 1')
        
        # Redirect to the audio test page with all data
        return redirect(url_for('main.audio_test', **symptom_args))
    
    # On a GET request, just display the symptom form.
    return render_template('new_test.html', title='New Test - Step 1')

# STAGE 2: Serves the audio form and handles the final combined prediction.
@bp.route('/audio_test', methods=['GET', 'POST'])
@login_required
def audio_test():
    """On GET, displays audio form. On POST, runs both models and saves the report."""
    if request.method == 'POST':
        # Determine which audio file source was used.
        if 'uploaded_audio_data' in request.files and request.files['uploaded_audio_data'].filename != '':
            file = request.files['uploaded_audio_data']
        elif 'recorded_audio_data' in request.files and request.files['recorded_audio_data'].filename != '':
            file = request.files['recorded_audio_data']
        else:
            flash('No audio file was provided. Please record or upload a file.', 'danger')
            return redirect(url_for('main.audio_test', **request.form))

        # --- Prepare data for BOTH models ---
        
        # 1. Prepare data for Symptom Model (M1)
        symptom_data_for_model = {
            'tremor': 1 if request.form.get('tremor') != 'no' else 0,
            'stiffness': 1 if request.form.get('stiffness') == 'yes' else 0,
            'walking_issue': 1 if request.form.get('balance') == 'yes' else 0 # Correctly use 'balance' from form for 'walking_issue' feature
        }

        # 2. Get user age and gender
        age = request.form.get('age', type=int)
        gender = request.form.get('gender')

        if not age or not gender:
            flash('Required user data was lost. Please start the test over.', 'danger')
            return redirect(url_for('main.new_test'))
            
        # Save the audio file temporarily
        base_filename = secure_filename(file.filename if file.filename else "recording.webm")
        unique_filename = f"user_{current_user.id}_{datetime.utcnow().timestamp()}_{base_filename}"
        audio_path = os.path.join('temp_uploads', unique_filename)
        file.save(audio_path)
        
        # Call the master prediction function from ml_logic
        final_result, cnn_result, cnn_pred_value = get_combined_prediction(symptom_data_for_model, audio_path, age)
        
        # Create a detailed string for the database report
        symptoms_for_report = (
            f"Tremor: {request.form.get('tremor', 'N/A').replace('_', ' ').title()}, "
            f"Stiffness: {request.form.get('stiffness', 'N/A').title()}, "
            f"Balance: {request.form.get('balance', 'N/A').title()}. "
            f"Other Notes: {request.form.get('other_symptoms', 'None')}"
        )

        # Save the final report to the database
        report = Report(age=age, gender=gender, symptoms=symptoms_for_report, cnn_prediction=cnn_pred_value, cnn_result=cnn_result, final_result=final_result, author=current_user)
        db.session.add(report)
        db.session.commit()

        # Prepare a dictionary for the email template for nicer formatting
        symptoms_for_email = {
            "Tremor": request.form.get('tremor', 'N/A').replace('_', ' ').title(),
            "Stiffness or Slowness": request.form.get('stiffness', 'N/A').title(),
            "Balance Issues": request.form.get('balance', 'N/A').title(),
            "Other Notes": request.form.get('other_symptoms', 'None')
        }
        send_email(
            '[Parkinson Detection System] Your Test Result',
            sender=current_app.config['ADMINS'][0], recipients=[current_user.email],
            text_body=render_template('email/result_notification.txt', user=current_user, report=report, symptoms=symptoms_for_email),
            html_body=render_template('email/result_notification.html', user=current_user, report=report, symptoms=symptoms_for_email)
        )
        
        flash('Your test is complete! The result has been sent to your email and is available on your dashboard.', 'success')
        if os.path.exists(audio_path): os.remove(audio_path)
        return redirect(url_for('main.dashboard'))
    
    # For a GET request, pass URL parameters to the template as hidden fields
    symptom_data = request.args.to_dict()
    return render_template('audio_test.html', title='New Test - Step 2', symptom_data=symptom_data)

# =============================================================================
# === ADMIN ROUTES
# =============================================================================
@bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    user_count = User.query.count()
    report_count = Report.query.count()
    result_stats = db.session.query(Report.final_result, func.count(Report.final_result)).group_by(Report.final_result).all()
    chart_labels = [result for result, count in result_stats]
    chart_data = [count for result, count in result_stats]
    return render_template(
        'admin/dashboard.html', 
        title='Admin Dashboard', 
        user_count=user_count, 
        report_count=report_count,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

@bp.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.id).all()
    return render_template('admin/users.html', title='Manage Users', users=users)