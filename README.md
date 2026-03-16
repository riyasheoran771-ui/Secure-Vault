# Secure-Vault
Secure Vault Classic 🔒
A secure document sharing platform built with Flask, featuring advanced print settings and role-based access control.
Features ✨
Document Security
Encrypted Storage: Files stored with Fernet encryption
Secure Sharing: Token-based access with optional password protection
Access Control: View limits, expiry dates, device restrictions
Audit Logging: Complete activity tracking with IP addresses
Advanced Print Settings 🖨️
Paper Sizes: A4, A3, A2, Letter, Legal, Tabloid
Orientation: Portrait or Landscape
Margins: None, Normal, Wide
Scale: 50% - 150% zoom
Page Breaks: Custom page break placement
Headers/Footers: Page numbers, document title, print date
Background Options: White or Default
User Management
Role-based access (User/Admin)
JWT authentication
Profile management
Admin dashboard
File Support
PDF documents with preview
Images (JPG, PNG, GIF, WebP, BMP)
Office documents (DOCX, XLSX, PPTX)
Text files (TXT, MD, CSV, JSON)
Tech Stack 🛠️
Backend:
Flask 3.0.0
SQLAlchemy ORM
SQLite Database
Flask-Login for authentication
Flask-WTF for forms
Flask-Limiter for rate limiting
bcrypt for password hashing
PyPDF2 for PDF handling
Cryptography library for encryption
Frontend:
Jinja2 Templates
Tailwind CSS
Vanilla JavaScript
PDF.js for PDF rendering
Installation 🚀
Prerequisites
Python 3.8+
pip package manager
Setup
Clone the repository
```bash
git clone <your-repo-url>
cd secure-vault-classic
```
Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```
Install dependencies
```bash
pip install -r requirements.txt
```
Configure environment variables
```bash
cp .env.example .env
# Edit .env and set your secrets
```
Initialize database
```bash
python app.py
# Or run: flask init-db
```
Run the application
```bash
python app.py
# Access at http://localhost:5000
```
Configuration ⚙️
Environment Variables (.env)
```env
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///secure_vault.db
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216  # 16MB max upload
```
Default Admin Account
Email: admin@securevault.com
Password: Admin@123456
Change these immediately in production!
Project Structure 📁
```
secure-vault-classic/
├── routes/              # Application routes
│   ├── __init__.py
│   ├── auth.py         # Authentication routes
│   ├── documents.py    # Document management
│   └── admin.py        # Admin panel
├── templates/          # Jinja2 templates
│   ├── base.html
│   ├── auth/           # Login/Register
│   ├── admin/          # Admin pages
│   └── ...
├── static/
│   ├── uploads/        # Uploaded files (not tracked)
│   ├── css/
│   └── js/
├── utils/              # Utility functions
│   ├── security.py     # Encryption & hashing
│   └── decorators.py   # Route decorators
├── instance/           # Database files (not tracked)
├── .env                # Environment variables (not tracked)
├── .env.example        # Example configuration
├── .gitignore
├── app.py              # Main application
├── config.py           # Configuration classes
├── models.py           # Database models
└── requirements.txt    # Python dependencies
```
Usage Guide 📖
Upload Documents
Navigate to Upload page
Drag & drop or select file
Set security options:
View limit (number of views)
Expiry date/time
Password protection
Device restriction
Allow download/print
Click "Upload Document"
Share the generated link
Share Documents
Copy shareable link
Share via social media (WhatsApp, X, LinkedIn, Telegram)
Send password separately if protected
Print Documents
Open shared link
Click "Print" button
Configure print settings:
Basic: Paper size, orientation, margins, scale
Advanced: Page breaks, headers/footers, background
Click "Print" to open browser print dialog
Admin Panel
Access from user dashboard (visible to admins only)
Manage users and documents
View activity logs
System statistics
Security Features 🔐
Password Hashing: bcrypt with salt rounds
File Encryption: Fernet symmetric encryption
CSRF Protection: Flask-WTF tokens on all forms
Rate Limiting: Prevent brute force attacks
Session Management: Secure cookie-based sessions
SQL Injection Prevention: SQLAlchemy ORM parameterization
XSS Protection: Jinja2 auto-escaping
API Routes 🛣️
Authentication
`POST /register` - Create new account
`POST /login` - User login
`GET /logout` - User logout
Documents
`POST /upload` - Upload document
`GET /share/<token>` - View shared document
`GET /download/<token>` - Download document
`GET /print/<token>` - Print document
`DELETE /document/<id>` - Delete document
Activity
`GET /dashboard` - User dashboard with activity log
`GET /profile` - User profile
Admin
`GET /admin` - Admin dashboard
`GET /admin/users` - User management
`GET /admin/documents` - Document management
`GET /admin/logs` - Activity logs
Troubleshooting 🔧
Port 5000 Already in Use
If you're on macOS and port 5000 is blocked by AirPlay:
```bash
# Use different port
flask run --port 5001
```
Database Issues
```bash
# Remove old database and reinitialize
rm instance/*.db
python app.py
```
Upload Not Working
Check `.env` has correct `UPLOAD_FOLDER`
Verify `MAX_CONTENT_LENGTH` setting
Ensure `static/uploads/` directory exists
Development 👨‍💻
Running Tests
```bash
pytest tests/
```
Code Style
Follow PEP 8 guidelines
Use type hints where possible
Add docstrings to functions
Deployment 🚀
Production Server
Use Gunicorn (included in requirements):
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```
Environment Variables for Production
```env
FLASK_ENV=production
SECRET_KEY=<strong-random-key>
JWT_SECRET_KEY=<strong-random-key>
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```
License 📄
MIT License - Feel free to use this project for learning or commercial purposes.
Contributing 🤝
Fork the repository
Create feature branch (`git checkout -b feature/AmazingFeature`)
Commit changes (`git commit -m 'Add AmazingFeature'`)
Push to branch (`git push origin feature/AmazingFeature`)
Open Pull Request
Acknowledgments 🙏
Flask community
Tailwind CSS team
All contributors
Contact 📧
For questions or support, please open an issue on GitHub.
---
Built with ❤️ using Flask
