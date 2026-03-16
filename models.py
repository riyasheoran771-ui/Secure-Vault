from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import bcrypt
import uuid
import secrets
import string

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())

def generate_share_token():
    """Generate a secure random token for document sharing"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    profile_image = db.Column(db.String(255), nullable=True)
    
    documents = db.relationship('Document', backref='owner', lazy=True, cascade='all, delete-orphan')
    activities = db.relationship('ActivityLog', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)
    tags = db.Column(db.String(500), nullable=True)
    
    share_token = db.Column(db.String(64), unique=True, default=generate_share_token)
    password_hash = db.Column(db.String(255), nullable=True)
    
    expiry_date = db.Column(db.DateTime, nullable=True)
    view_limit = db.Column(db.Integer, default=0)
    current_views = db.Column(db.Integer, default=0)
    download_limit = db.Column(db.Integer, default=0)
    current_downloads = db.Column(db.Integer, default=0)
    
    allow_download = db.Column(db.Boolean, default=True)
    allow_print = db.Column(db.Boolean, default=True)
    allow_share = db.Column(db.Boolean, default=True)
    device_restriction = db.Column(db.String(20), default='both')
    watermark_enabled = db.Column(db.Boolean, default=False)
    
    is_active = db.Column(db.Boolean, default=True)
    is_revoked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    activities = db.relationship('ActivityLog', backref='document', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        if password:
            salt = bcrypt.gensalt(rounds=12)
            self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        if not self.password_hash:
            return True
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def is_expired(self):
        return self.expiry_date and datetime.utcnow() > self.expiry_date
    
    def is_limit_reached(self):
        return self.view_limit > 0 and self.current_views >= self.view_limit
    
    def get_status(self):
        if self.is_revoked:
            return 'revoked'
        if self.is_expired():
            return 'expired'
        if self.is_limit_reached():
            return 'limit_reached'
        if not self.is_active:
            return 'inactive'
        return 'active'

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=True)
    
    action = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='success')
    
    ip_address = db.Column(db.String(45), nullable=True)
    device_type = db.Column(db.String(50), nullable=True)
    device_name = db.Column(db.String(100), nullable=True)
    browser = db.Column(db.String(100), nullable=True)
    os = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)