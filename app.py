import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
import uuid
import re

from config import config
from models import db, User, Document, ActivityLog, generate_share_token
from utils.security import get_device_info, check_device_restriction, format_file_size, is_allowed_file, get_file_extension

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    csrf = CSRFProtect(app)
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    # Admin required decorator
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role != 'admin':
                flash('Admin access required.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    
    # Helper: log activity
    def log_activity(action, document=None, status='success', details=None):
        user_agent = request.headers.get('User-Agent', '')
        device_info = get_device_info(user_agent)
        activity = ActivityLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            document_id=document.id if document else None,
            action=action,
            status=status,
            ip_address=request.remote_addr,
            device_type=device_info['device_type'],
            device_name=device_info['device_name'],
            browser=device_info['browser'],
            os=device_info['os'],
            user_agent=user_agent,
            details=details
        )
        db.session.add(activity)
        db.session.commit()
    
    # Context processor for templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
    
    # ==================== ROUTES ====================
    
    # Landing Page
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
    
    # Register
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            username = request.form.get('username', '').strip().lower()
            email = request.form.get('email', '').strip().lower()
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            errors = []
            if not full_name:
                errors.append('Full name is required.')
            if not username or len(username) < 3:
                errors.append('Username must be at least 3 characters.')
            if not email or not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                errors.append('Valid email is required.')
            if not password or len(password) < 8:
                errors.append('Password must be at least 8 characters.')
            if password != confirm_password:
                errors.append('Passwords do not match.')
            
            if User.query.filter_by(username=username).first():
                errors.append('Username already exists.')
            if User.query.filter_by(email=email).first():
                errors.append('Email already registered.')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return render_template('auth/register.html')
            
            # Create user
            user = User(full_name=full_name, username=username, email=email, phone=phone)
            user.set_password(password)
            
            # First user becomes admin
            if User.query.count() == 0:
                user.role = 'admin'
            
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        return render_template('auth/register.html')
    
    # Login
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username_or_email = request.form.get('username_or_email', '').strip()
            password = request.form.get('password', '')
            remember = request.form.get('remember') == 'on'
            
            user = User.query.filter(
                db.or_(User.username == username_or_email.lower(), User.email == username_or_email.lower())
            ).first()
            
            if not user or not user.check_password(password):
                flash('Invalid username/email or password.', 'error')
                return render_template('auth/login.html')
            
            if not user.is_active:
                flash('Your account has been suspended.', 'error')
                return render_template('auth/login.html')
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.full_name}!', 'success')
            
            # Log login
            next_page = request.args.get('next')
            if user.role == 'admin':
                return redirect(next_page or url_for('admin_dashboard'))
            return redirect(next_page or url_for('dashboard'))
        
        return render_template('auth/login.html')
    
    # Logout
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'success')
        return redirect(url_for('login'))
    
    # User Dashboard
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Stats
        total_docs = Document.query.filter_by(user_id=current_user.id).count()
        active_docs = Document.query.filter_by(user_id=current_user.id, is_active=True, is_revoked=False).count()
        total_views = db.session.query(db.func.sum(Document.current_views)).filter_by(user_id=current_user.id).scalar() or 0
        total_downloads = db.session.query(db.func.sum(Document.current_downloads)).filter_by(user_id=current_user.id).scalar() or 0
        
        # Documents
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status', 'all')
        search = request.args.get('search', '').strip()
        
        query = Document.query.filter_by(user_id=current_user.id)
        
        if status_filter == 'active':
            query = query.filter_by(is_active=True, is_revoked=False)
        elif status_filter == 'expired':
            query = query.filter(Document.expiry_date < datetime.utcnow())
        elif status_filter == 'revoked':
            query = query.filter_by(is_revoked=True)
        
        if search:
            query = query.filter(
                db.or_(
                    Document.title.ilike(f'%{search}%'),
                    Document.original_filename.ilike(f'%{search}%')
                )
            )
        
        documents = query.order_by(Document.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
        
        # All activities - get ALL activities for documents owned by current user
        activities = ActivityLog.query.join(
            Document, ActivityLog.document_id == Document.id
        ).filter(
            Document.user_id == current_user.id
        ).order_by(ActivityLog.created_at.desc()).all()
        
        return render_template('dashboard.html',
            total_docs=total_docs, active_docs=active_docs,
            total_views=total_views, total_downloads=total_downloads,
            documents=documents, activities=activities,
            status_filter=status_filter, search=search, format_file_size=format_file_size
        )
    
    # Upload Document
    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload():
        if request.method == 'POST':
            print("=" * 50)
            print("UPLOAD POST REQUEST RECEIVED")
            print(f"Files in request: {list(request.files.keys())}")
            print(f"Form data: {list(request.form.keys())}")
            print("=" * 50)
            
            if 'file' not in request.files:
                flash('No file selected.', 'error')
                print("ERROR: No 'file' in request.files")
                return redirect(url_for('upload'))
            
            file = request.files['file']
            print(f"File received: {file.filename}")
            
            if file.filename == '':
                flash('No file selected.', 'error')
                print("ERROR: Empty filename")
                return redirect(url_for('upload'))
            
            if not is_allowed_file(file.filename):
                flash('File type not allowed.', 'error')
                print(f"ERROR: File type not allowed: {file.filename}")
                return redirect(url_for('upload'))
            
            # Get form data
            title = request.form.get('title', '').strip() or file.filename.rsplit('.', 1)[0]
            description = request.form.get('description', '').strip()
            category = request.form.get('category', '').strip()
            tags = request.form.get('tags', '').strip()
            
            # Security settings
            expiry_option = request.form.get('expiry_option', '7days')
            custom_expiry = request.form.get('custom_expiry_days', '')
            view_limit_option = request.form.get('view_limit_option', 'unlimited')
            custom_view_limit = request.form.get('custom_view_limit', '')
            password = request.form.get('doc_password', '')
            device_restriction = request.form.get('device_restriction', 'both')
            allow_download = request.form.get('allow_download') == 'on'
            allow_print = request.form.get('allow_print') == 'on'
            watermark = request.form.get('watermark') == 'on'
            
            # Calculate expiry
            expiry_map = {'1day': 1, '7days': 7, '30days': 30, 'never': None, 'custom': None}
            if expiry_option == 'custom' and custom_expiry:
                expiry_date = datetime.utcnow() + timedelta(days=int(custom_expiry))
            elif expiry_option == 'never':
                expiry_date = None
            else:
                days = expiry_map.get(expiry_option, 7)
                expiry_date = datetime.utcnow() + timedelta(days=days) if days else None
            
            # View limit - handle both preset and custom values
            view_map = {'10': 10, '50': 50, '100': 100, 'unlimited': 0}
            
            # Check if it's a preset value
            if view_limit_option in view_map:
                view_limit = view_map[view_limit_option]
            elif view_limit_option.isdigit():
                # It's a custom numeric value from the input
                view_limit = int(view_limit_option)
            elif custom_view_limit and custom_view_limit.isdigit():
                # Fallback to custom_view_limit field
                view_limit = int(custom_view_limit)
            else:
                view_limit = 0  # Unlimited
            
            # Save file
            file_ext = get_file_extension(file.filename)
            stored_filename = f"{uuid.uuid4().hex}.{file_ext}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            
            # Create document
            document = Document(
                user_id=current_user.id,
                original_filename=file.filename,
                stored_filename=stored_filename,
                file_type=file_ext,
                file_size=file_size,
                mime_type=file.content_type or 'application/octet-stream',
                title=title,
                description=description,
                category=category,
                tags=tags,
                expiry_date=expiry_date,
                view_limit=view_limit,
                device_restriction=device_restriction,
                allow_download=allow_download,
                allow_print=allow_print,
                watermark_enabled=watermark
            )
            
            if password:
                document.set_password(password)
            
            db.session.add(document)
            db.session.commit()
            
            # Log upload activity
            user_agent = request.headers.get('User-Agent', '')
            device_info = get_device_info(user_agent)
            activity = ActivityLog(
                document_id=document.id,
                action='upload',
                ip_address=request.remote_addr,
                device_type=device_info['device_type'],
                device_name=device_info['device_name'],
                browser=device_info['browser'],
                os=device_info['os'],
                user_agent=user_agent
            )
            db.session.add(activity)
            db.session.commit()
            
            print(f"SUCCESS: Document created with ID: {document.id}")
            print(f"  Title: {document.title}")
            print(f"  Expiry: {document.expiry_date}")
            print(f"  View Limit: {document.view_limit}")
            print(f"  Device: {document.device_restriction}")
            
            flash('Document uploaded successfully!', 'success')
            return redirect(url_for('upload_success', doc_id=document.id))
        
        return render_template('upload.html')
    
    # Upload Success
    @app.route('/upload-success/<doc_id>')
    @login_required
    def upload_success(doc_id):
        document = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
        share_url = url_for('share_view', token=document.share_token, _external=True)
        return render_template('upload_success.html', document=document, share_url=share_url, format_file_size=format_file_size)
    
    # Document Actions
    @app.route('/document/<doc_id>/revoke')
    @login_required
    def revoke_document(doc_id):
        document = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
        document.is_revoked = True
        document.is_active = False
        db.session.commit()
        flash('Document access revoked.', 'success')
        return redirect(url_for('dashboard'))
    
    @app.route('/document/<doc_id>/regenerate')
    @login_required
    def regenerate_link(doc_id):
        document = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
        document.share_token = generate_share_token()
        document.is_revoked = False
        document.is_active = True
        db.session.commit()
        flash('Share link regenerated.', 'success')
        return redirect(url_for('dashboard'))
    
    @app.route('/document/<doc_id>/delete')
    @login_required
    def delete_document(doc_id):
        document = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.stored_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(document)
        db.session.commit()
        flash('Document deleted.', 'success')
        return redirect(url_for('dashboard'))
    
    # Share View (Public)
    @app.route('/share/<token>', methods=['GET', 'POST'])
    def share_view(token):
        document = Document.query.filter_by(share_token=token).first_or_404()
        user_agent = request.headers.get('User-Agent', '')
        device_info = get_device_info(user_agent)
        
        # Check restrictions
        if document.is_revoked:
            return render_template('share_error.html', error='Access Revoked', message='The owner has revoked access to this document.')
        
        if document.is_expired():
            return render_template('share_error.html', error='Link Expired', message='This share link has expired.')
        
        if document.is_limit_reached():
            return render_template('share_error.html', error='Limit Reached', message='This document has reached its view limit.')
        
        if not check_device_restriction(user_agent, document.device_restriction):
            return render_template('share_error.html', error='Device Restricted', 
                message=f'This document can only be accessed from {document.device_restriction} devices.')
        
        # Password check
        if document.password_hash:
            if request.method == 'POST':
                password = request.form.get('password', '')
                if not document.check_password(password):
                    flash('Incorrect password.', 'error')
                    return render_template('share_view.html', document=document, requires_password=True, format_file_size=format_file_size)
            else:
                return render_template('share_view.html', document=document, requires_password=True, format_file_size=format_file_size)
        
        return render_template('share_view.html', document=document, requires_password=False, format_file_size=format_file_size, device_info=device_info)
    
    # View Document - Shows document in viewer with controls
    @app.route('/share/<token>/view')
    def view_document(token):
        document = Document.query.filter_by(share_token=token).first_or_404()
        
        # Check all restrictions
        if document.is_revoked or document.is_expired() or document.is_limit_reached():
            flash('Cannot view document.', 'error')
            return redirect(url_for('share_view', token=token))
        
        # Increment view count
        document.current_views += 1
        db.session.commit()
        
        # Log view
        user_agent = request.headers.get('User-Agent', '')
        device_info = get_device_info(user_agent)
        activity = ActivityLog(
            document_id=document.id,
            action='view',
            ip_address=request.remote_addr,
            device_type=device_info['device_type'],
            device_name=device_info['device_name'],
            browser=device_info['browser'],
            os=device_info['os'],
            user_agent=user_agent
        )
        db.session.add(activity)
        db.session.commit()
        
        return render_template('document_viewer.html', document=document, format_file_size=format_file_size)
    
    # Serve Document File - Raw file for embedding
    @app.route('/share/<token>/file')
    def serve_document(token):
        document = Document.query.filter_by(share_token=token).first_or_404()
        
        # Check restrictions
        if document.is_revoked or document.is_expired() or document.is_limit_reached():
            abort(403)
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.stored_filename)
        return send_file(file_path, mimetype=document.mime_type)
    
    # Download Document
    @app.route('/share/<token>/download')
    def download_document(token):
        document = Document.query.filter_by(share_token=token).first_or_404()
        
        if not document.allow_download:
            flash('Download not allowed.', 'error')
            return redirect(url_for('share_view', token=token))
        
        # Increment download count
        document.current_downloads += 1
        db.session.commit()
        
        # Log download
        user_agent = request.headers.get('User-Agent', '')
        device_info = get_device_info(user_agent)
        activity = ActivityLog(
            document_id=document.id,
            action='download',
            ip_address=request.remote_addr,
            device_type=device_info['device_type'],
            device_name=device_info['device_name'],
            browser=device_info['browser'],
            os=device_info['os'],
            user_agent=user_agent
        )
        db.session.add(activity)
        db.session.commit()
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.stored_filename)
        return send_file(file_path, mimetype=document.mime_type, as_attachment=True, download_name=document.original_filename)
    
    # Print Document - Opens viewer with auto-print
    @app.route('/share/<token>/print')
    def print_document(token):
        document = Document.query.filter_by(share_token=token).first_or_404()
        
        if not document.allow_print:
            flash('Print not allowed.', 'error')
            return redirect(url_for('share_view', token=token))
        
        # Log print
        user_agent = request.headers.get('User-Agent', '')
        device_info = get_device_info(user_agent)
        activity = ActivityLog(
            document_id=document.id,
            action='print',
            ip_address=request.remote_addr,
            device_type=device_info['device_type'],
            device_name=device_info['device_name'],
            browser=device_info['browser'],
            os=device_info['os'],
            user_agent=user_agent
        )
        db.session.add(activity)
        db.session.commit()
        
        return render_template('document_viewer.html', document=document, format_file_size=format_file_size, auto_print=True)
    
    # Profile
    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'update_profile':
                current_user.full_name = request.form.get('full_name', '').strip()
                current_user.phone = request.form.get('phone', '').strip()
                db.session.commit()
                flash('Profile updated.', 'success')
            
            elif action == 'change_password':
                current_password = request.form.get('current_password', '')
                new_password = request.form.get('new_password', '')
                confirm_password = request.form.get('confirm_password', '')
                
                if not current_user.check_password(current_password):
                    flash('Current password is incorrect.', 'error')
                elif new_password != confirm_password:
                    flash('New passwords do not match.', 'error')
                elif len(new_password) < 8:
                    flash('Password must be at least 8 characters.', 'error')
                else:
                    current_user.set_password(new_password)
                    db.session.commit()
                    flash('Password changed successfully.', 'success')
        
        return render_template('profile.html')
    
    # Admin Dashboard
    @app.route('/admin')
    @login_required
    @admin_required
    def admin_dashboard():
        # Stats
        total_users = User.query.count()
        total_docs = Document.query.count()
        total_views = db.session.query(db.func.sum(Document.current_views)).scalar() or 0
        today_logins = ActivityLog.query.filter(
            ActivityLog.action == 'login',
            db.func.date(ActivityLog.created_at) == datetime.utcnow().date()
        ).count()
        
        # Recent users
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        
        # Recent documents
        recent_docs = Document.query.order_by(Document.created_at.desc()).limit(5).all()
        
        # Recent activities
        recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
        
        return render_template('admin/dashboard.html',
            total_users=total_users, total_docs=total_docs,
            total_views=total_views, today_logins=today_logins,
            recent_users=recent_users, recent_docs=recent_docs,
            recent_activities=recent_activities, format_file_size=format_file_size,
            now=datetime.utcnow()
        )
    
    # Admin Users
    @app.route('/admin/users')
    @login_required
    @admin_required
    def admin_users():
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '').strip()
        
        query = User.query
        if search:
            query = query.filter(
                db.or_(
                    User.full_name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                    User.username.ilike(f'%{search}%')
                )
            )
        
        users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
        return render_template('admin/users.html', users=users, search=search)
    
    @app.route('/admin/user/<user_id>/suspend')
    @login_required
    @admin_required
    def admin_suspend_user(user_id):
        user = User.query.get_or_404(user_id)
        if user.role == 'admin':
            flash('Cannot suspend admin user.', 'error')
        else:
            user.is_active = False
            db.session.commit()
            flash('User suspended.', 'success')
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/user/<user_id>/activate')
    @login_required
    @admin_required
    def admin_activate_user(user_id):
        user = User.query.get_or_404(user_id)
        user.is_active = True
        db.session.commit()
        flash('User activated.', 'success')
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/user/<user_id>/delete')
    @login_required
    @admin_required
    def admin_delete_user(user_id):
        user = User.query.get_or_404(user_id)
        if user.role == 'admin':
            flash('Cannot delete admin user.', 'error')
        else:
            # Delete user files
            for doc in user.documents:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.stored_filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            db.session.delete(user)
            db.session.commit()
            flash('User deleted.', 'success')
        return redirect(url_for('admin_users'))
    
    # Admin Documents
    @app.route('/admin/documents')
    @login_required
    @admin_required
    def admin_documents():
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '').strip()
        
        query = Document.query
        if search:
            query = query.filter(Document.title.ilike(f'%{search}%'))
        
        documents = query.order_by(Document.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
        return render_template('admin/documents.html', documents=documents, search=search, format_file_size=format_file_size)
    
    # Admin Logs
    @app.route('/admin/logs')
    @login_required
    @admin_required
    def admin_logs():
        page = request.args.get('page', 1, type=int)
        logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(page=page, per_page=50, error_out=False)
        return render_template('admin/logs.html', logs=logs)
    
    # Create tables
    with app.app_context():
        db.create_all()
        # Create default admin
        if User.query.count() == 0:
            admin = User(full_name='System Admin', username='admin', email='admin@securevault.com', role='admin')
            admin.set_password('Admin@123456')
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: admin@securevault.com / Admin@123456")
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=8000, host='0.0.0.0')