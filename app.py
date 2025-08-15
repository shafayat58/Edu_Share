import os
import argparse
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    os.makedirs(app.instance_path, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'edushare.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    return app

app = create_app()
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# -------------------- Models --------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    folders = db.relationship('Folder', backref='owner', lazy=True)
    resources = db.relationship('Resource', backref='uploader', lazy=True)
    reviews = db.relationship('Review', backref='reviewer', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    parent = db.relationship('Folder', remote_side=[id], backref='children')

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=True)
    subject = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(300), nullable=False)
    mimetype = db.Column(db.String(120), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)

    folder = db.relationship('Folder', backref='resources')
    reviews = db.relationship('Review', backref='resource', lazy=True, cascade="all, delete-orphan")

    @property
    def avg_rating(self):
        if not self.reviews:
            return None
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 2)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)  # 1..10
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'resource_id', name='uix_user_resource'),
    )

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------- Routes: Auth --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'error')
            return redirect(url_for('register'))
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'success')
    return redirect(url_for('login'))

# -------------------- Routes: Explorer --------------------
def get_breadcrumbs(folder):
    crumbs = []
    while folder:
        crumbs.append(folder)
        folder = folder.parent
    return list(reversed(crumbs))

@app.route('/')
@login_required
def dashboard():
    root_folders = Folder.query.filter_by(owner_id=current_user.id, parent_id=None).all()
    loose_resources = Resource.query.filter_by(uploader_id=current_user.id, folder_id=None).all()
    return render_template('dashboard.html', root_folders=root_folders, resources=loose_resources, breadcrumbs=[])

@app.route('/folder/<int:folder_id>')
@login_required
def folder_view(folder_id):
    folder = Folder.query.filter_by(id=folder_id, owner_id=current_user.id).first_or_404()
    return render_template('dashboard.html',
                           current_folder=folder,
                           root_folders=folder.children,
                           resources=folder.resources,
                           breadcrumbs=get_breadcrumbs(folder))

@app.route('/folder/create', methods=['POST'])
@login_required
def folder_create():
    name = request.form['name'].strip()
    parent_id = request.form.get('parent_id')
    if not name:
        flash('Folder name is required.', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    folder = Folder(name=name, owner_id=current_user.id, parent_id=parent_id or None)
    db.session.add(folder)
    db.session.commit()
    flash('Folder created.', 'success')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/folder/<int:folder_id>/delete', methods=['POST'])
@login_required
def folder_delete(folder_id):
    folder = Folder.query.filter_by(id=folder_id, owner_id=current_user.id).first_or_404()
    if folder.children or folder.resources:
        flash('Folder is not empty.', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    db.session.delete(folder)
    db.session.commit()
    flash('Folder deleted.', 'success')
    return redirect(url_for('dashboard'))

# -------------------- Routes: Upload & Files --------------------
ALLOWED_EXTENSIONS = set(['pdf','txt','md','zip','mp4','avi','mkv','mov','doc','docx','ppt','pptx','xls','xlsx','csv','png','jpg','jpeg','gif','webm','webp'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    title = request.form.get('title', '').strip() or 'Untitled'
    author = request.form.get('author', '').strip()
    subject = request.form.get('subject', '').strip()
    description = request.form.get('description', '').strip()
    folder_id = request.form.get('folder_id') or None
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('No file selected.', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    if not allowed_file(file.filename):
        flash('File type not allowed.', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)
    res = Resource(title=title, author=author, subject=subject, description=description,
                   filename=filename, mimetype=file.mimetype, uploader_id=current_user.id,
                   folder_id=folder_id)
    db.session.add(res)
    db.session.commit()
    flash('Uploaded!', 'success')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/download/<int:resource_id>')
@login_required
def download(resource_id):
    res = Resource.query.get_or_404(resource_id)
    # Access control: allow if uploader or public (for now, authorizes everyone logged in)
    return send_from_directory(app.config['UPLOAD_FOLDER'], res.filename, as_attachment=True)

@app.route('/resource/<int:resource_id>')
@login_required
def resource_detail(resource_id):
    res = Resource.query.get_or_404(resource_id)
    return render_template('resource.html', res=res)

@app.route('/resource/<int:resource_id>/delete', methods=['POST'])
@login_required
def resource_delete(resource_id):
    res = Resource.query.get_or_404(resource_id)
    if res.uploader_id != current_user.id:
        abort(403)
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], res.filename))
    except FileNotFoundError:
        pass
    db.session.delete(res)
    db.session.commit()
    flash('Resource deleted.', 'success')
    return redirect(request.referrer or url_for('dashboard'))

# -------------------- Routes: Review & Rating --------------------
@app.route('/resource/<int:resource_id>/review', methods=['POST'])
@login_required
def submit_review(resource_id):
    res = Resource.query.get_or_404(resource_id)
    rating = int(request.form.get('rating', 0))
    comment = request.form.get('comment', '').strip()
    rating = max(1, min(10, rating))
    existing = Review.query.filter_by(user_id=current_user.id, resource_id=res.id).first()
    if existing:
        existing.rating = rating
        existing.comment = comment
    else:
        db.session.add(Review(rating=rating, comment=comment, user_id=current_user.id, resource_id=res.id))
    db.session.commit()
    flash('Review saved.', 'success')
    return redirect(url_for('resource_detail', resource_id=res.id))

# -------------------- Routes: Search --------------------
@app.route('/search')
@login_required
def search():
    q = request.args.get('q', '').strip()
    author = request.args.get('author', '').strip()
    subject = request.args.get('subject', '').strip()
    sort = request.args.get('sort', '').strip()  # 'rating' or ''
    query = Resource.query

    if q:
        like = f"%{q}%"
        query = query.filter(Resource.title.ilike(like))
    if author:
        query = query.filter(Resource.author.ilike(f"%{author}%"))
    if subject:
        query = query.filter(Resource.subject.ilike(f"%{subject}%"))

    results = query.all()
    if sort == 'rating':
        results.sort(key=lambda r: (r.avg_rating or 0), reverse=True)

    return render_template('search.html', results=results, q=q, author=author, subject=subject, sort=sort)

# -------------------- CLI helper --------------------
if __name__ == '__main__':
    # -------------------- App startup --------------------
    # Ensure tables exist automatically when app starts
    with app.app_context():
        db.create_all()
        print('Database is ready at', app.config['SQLALCHEMY_DATABASE_URI'])
    
    # Start the Flask development server
    app.run(debug=True)
