import os
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import jsonify

app = Flask(__name__)
app.secret_key = 'art_top_secret'

# --- КОНФИГУРАЦИЯ ТИПОВ ---
CONTENT_TYPES = ["Drawing", "Tutorial", "Pose", "Gamma", "Character Design", "Other"]

# DB Config
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')
db = SQLAlchemy(app)

# Делаем CONTENT_TYPES доступным во всех шаблонах автоматически
@app.context_processor
def inject_types():
    return dict(content_types=CONTENT_TYPES)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Publication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=True)
    hashtags = db.Column(db.String(200))
    pub_type = db.Column(db.String(50)) # Drawing, Tutorial, Pose, Gamma
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(100))
    
    # Helper to retrieve date/time could be added here for "freshness", 
    # relying on ID order for now as proxy for "freshness"

with app.app_context():
    db.create_all()

# --- ROUTES ---

@app.route('/')
def index(): return render_template('index.html')

@app.route('/auth')
def auth(): return render_template('auth.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        if User.query.filter_by(email=email).first():
            return "Email exists!"
        hashed_pw = generate_password_hash(request.form['password'])
        new_user = User(username=request.form['name'], email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password, password):
            return "Error: Wrong credentials"
            
        session['user_id'] = user.id
        return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('auth'))
    
    active_type = request.args.get('pub_type', 'Все типы')
    search_query = request.args.get('search') # Это может быть текст или слово "Все"
    page = request.args.get('page', 1, type=int)
    
    # Базовый запрос с учетом фильтра по типу
    query = Publication.query
    if active_type != 'Все типы':
        query = query.filter_by(pub_type=active_type)

    # РЕЖИМ ПЛИТКИ (GRID): включается только если есть параметр search
    if search_query is not None:
        # Если поиск не пустой и не равен "Все", фильтруем по тегам
        if search_query.strip() and search_query != 'Все':
            query = query.filter(Publication.hashtags.contains(search_query))
        
        pagination = query.order_by(Publication.id.desc()).paginate(page=page, per_page=30, error_out=False)
        
        return render_template('home.html', 
                               mode='grid', 
                               pubs=pagination.items, 
                               search_query=search_query, 
                               active_type=active_type,
                               next_page=page+1 if pagination.has_next else None)

    # РЕЖИМ ЛЕНТ (FEED): по умолчанию и при переключении табов
    all_pubs = query.order_by(Publication.id.desc()).all()
    
    # Собираем теги только из отфильтрованных по типу публикаций
    all_tags = []
    for p in all_pubs:
        if p.hashtags:
            tags = [t.strip().replace('#', '') for t in p.hashtags.replace(' ', ',').split(',') if t.strip()]
            all_tags.extend(tags)
    
    top_tags = [tag for tag, count in Counter(all_tags).most_common(5)]
    
    return render_template('home.html', 
                           mode='feed', 
                           all_pubs=all_pubs, 
                           top_tags=top_tags, 
                           active_type=active_type,
                           search_query=None) # Явно передаем None

@app.route('/publish', methods=['GET', 'POST'])
def create_pub():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        file = request.files['image']
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            new_pub = Publication(
                image=filename,
                description=request.form['description'],
                hashtags=request.form['hashtags'],
                pub_type=request.form['pub_type'],
                author_id=session['user_id'],
                title=request.form['title']
            )
            db.session.add(new_pub)
            db.session.commit()
            return redirect(url_for('home'))
        
    return render_template('create_pub.html', pub=None)

@app.route('/delete/<int:id>')
def delete_pub(id):
    pub = Publication.query.get(id)
    if pub and pub.author_id == session.get('user_id'):
        db.session.delete(pub)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/get_post/<int:id>')
def get_post(id):
    pub = Publication.query.get_or_404(id)
    # Получаем имя автора
    author = User.query.get(pub.author_id)
    return jsonify({
        'id': pub.id,
        'image': pub.image,
        'description': pub.description,
        'hashtags': pub.hashtags,
        'pub_type': pub.pub_type,
        'author_name': author.username if author else "Unknown",
        'is_owner': pub.author_id == session.get('user_id')
    })

@app.route('/edit/<int:id>', methods=['POST'])
def edit_pub(id):
    pub = Publication.query.get_or_404(id)
    if pub.author_id != session.get('user_id'):
        return "Access Denied", 403
    
    pub.description = request.form.get('description')
    pub.hashtags = request.form.get('hashtags')
    pub.pub_type = request.form.get('pub_type')
    db.session.commit()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
