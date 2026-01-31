import os
import time
import base64
from datetime import datetime
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'art_top_secret'

# --- КОНФИГУРАЦИЯ ТИПОВ ---
CONTENT_TYPES = ["Drawing", "Tutorial", "Pose", "Gamma", "Character Design", "Other"]

# DB Config
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')
db = SQLAlchemy(app)

@app.context_processor
def inject_types():
    return dict(content_types=CONTENT_TYPES)

# --- MODELS ---

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
    pub_type = db.Column(db.String(50)) 
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(100))

class Remix(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(200)) 
    original_pub_id = db.Column(db.Integer, db.ForeignKey('publication.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    author = db.relationship('User', backref='remixes')
    original = db.relationship('Publication', backref='remixes')

# Модель для комментариев к ремиксам
class RemixComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    remix_id = db.Column(db.Integer, db.ForeignKey('remix.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', backref='remix_comments')
    remix = db.relationship('Remix', backref='comments')

# [НОВОЕ] Модель для комментариев к оригинальным публикациям
class PublicationComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pub_id = db.Column(db.Integer, db.ForeignKey('publication.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', backref='pub_comments')
    publication = db.relationship('Publication', backref='comments')

# Модель для лайков публикаций
class PublicationLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pub_id = db.Column(db.Integer, db.ForeignKey('publication.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Уникальная пара: один пользователь может лайкнуть публикацию только один раз
    __table_args__ = (db.UniqueConstraint('pub_id', 'user_id', name='_pub_user_like_uc'),)
    
    user = db.relationship('User', backref='pub_likes')
    publication = db.relationship('Publication', backref='likes')

# Модель для лайков ремиксов
class RemixLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    remix_id = db.Column(db.Integer, db.ForeignKey('remix.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Уникальная пара: один пользователь может лайкнуть ремикс только один раз
    __table_args__ = (db.UniqueConstraint('remix_id', 'user_id', name='_remix_user_like_uc'),)
    
    user = db.relationship('User', backref='remix_likes')
    remix = db.relationship('Remix', backref='likes')

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
    search_query = request.args.get('search') 
    page = request.args.get('page', 1, type=int)
    
    query = Publication.query
    if active_type != 'Все типы':
        query = query.filter_by(pub_type=active_type)

    if search_query is not None:
        if search_query.strip() and search_query != 'Все':
            query = query.filter(Publication.hashtags.contains(search_query))
        
        pagination = query.order_by(Publication.id.desc()).paginate(page=page, per_page=30, error_out=False)
        
        return render_template('home.html', 
                               mode='grid', 
                               pubs=pagination.items, 
                               search_query=search_query, 
                               active_type=active_type,
                               next_page=page+1 if pagination.has_next else None)

    all_pubs = query.order_by(Publication.id.desc()).all()
    
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
                           search_query=None)

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
    author = User.query.get(pub.author_id)
    
    current_user_id = session.get('user_id')
    
    # Подсчет лайков и проверка, лайкнул ли текущий пользователь публикацию
    pub_like_count = PublicationLike.query.filter_by(pub_id=pub.id).count()
    pub_user_liked = False
    if current_user_id:
        pub_user_liked = PublicationLike.query.filter_by(pub_id=pub.id, user_id=current_user_id).first() is not None
    
    remixes_list = []
    remixes = Remix.query.filter_by(original_pub_id=pub.id).all()
    
    # Собираем данные ремиксов с количеством лайков
    for r in remixes:
        # Подсчет лайков для каждого ремикса
        remix_like_count = RemixLike.query.filter_by(remix_id=r.id).count()
        remix_user_liked = False
        if current_user_id:
            remix_user_liked = RemixLike.query.filter_by(remix_id=r.id, user_id=current_user_id).first() is not None
        
        remixes_list.append({
            'id': r.id,
            'image': r.image,
            'author_name': r.author.username,
            'author_id': r.author_id,
            'date': r.created_at.strftime('%d.%m.%Y'),
            'like_count': remix_like_count,
            'user_liked': remix_user_liked
        })
    
    # Сортируем ремиксы по количеству лайков (от большего к меньшему)
    remixes_list.sort(key=lambda x: x['like_count'], reverse=True)

    return jsonify({
        'id': pub.id,
        'image': pub.image,
        'description': pub.description,
        'hashtags': pub.hashtags,
        'pub_type': pub.pub_type,
        'author_name': author.username if author else "Unknown",
        'is_owner': pub.author_id == session.get('user_id'),
        'current_user_id': session.get('user_id'),
        'remixes': remixes_list,
        'like_count': pub_like_count,
        'user_liked': pub_user_liked
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

# --- EDITOR & REMIX ROUTES ---

@app.route('/editor/<int:original_id>')
def editor(original_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    pub = Publication.query.get_or_404(original_id)
    return render_template('editor.html', pub=pub)

@app.route('/save_remix', methods=['POST'])
def save_remix():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    image_data = data['image']
    original_id = data['original_id']
    
    try:
        header, encoded = image_data.split(",", 1)
        file_data = base64.b64decode(encoded)
        
        filename = f"remix_{original_id}_{int(time.time())}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, "wb") as f:
            f.write(file_data)
            
        new_remix = Remix(
            image=filename,
            original_pub_id=original_id,
            author_id=session['user_id']
        )
        db.session.add(new_remix)
        db.session.commit()
        
        return jsonify({'status': 'success', 'remix_id': new_remix.id})
    except Exception as e:
        print(e)
        return jsonify({'error': 'Failed to save'}), 500

@app.route('/delete_remix/<int:id>', methods=['POST'])
def delete_remix(id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    remix = Remix.query.get_or_404(id)
    if remix.author_id != session['user_id']:
        return jsonify({'error': 'Access Denied'}), 403
    
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], remix.image))
    except:
        pass
    
    db.session.delete(remix)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/add_remix_comment', methods=['POST'])
def add_remix_comment():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    text = data.get('text')
    remix_id = data.get('remix_id')
    
    if not text or not remix_id:
        return jsonify({'error': 'Missing data'}), 400
        
    comment = RemixComment(
        remix_id=remix_id,
        author_id=session['user_id'],
        text=text
    )
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'author': User.query.get(session['user_id']).username,
        'text': text,
        'date': datetime.utcnow().strftime('%d.%m.%Y %H:%M')
    })

@app.route('/get_remix_comments/<int:remix_id>')
def get_remix_comments(remix_id):
    comments = RemixComment.query.filter_by(remix_id=remix_id).order_by(RemixComment.created_at.asc()).all()
    result = []
    for c in comments:
        result.append({
            'author': c.author.username,
            'text': c.text,
            'date': c.created_at.strftime('%d.%m.%Y %H:%M')
        })
    return jsonify({'comments': result})

# [НОВОЕ] Добавление комментария к ОРИГИНАЛУ
@app.route('/add_pub_comment', methods=['POST'])
def add_pub_comment():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    text = data.get('text')
    pub_id = data.get('pub_id')
    
    if not text or not pub_id:
        return jsonify({'error': 'Missing data'}), 400
        
    comment = PublicationComment(
        pub_id=pub_id,
        author_id=session['user_id'],
        text=text
    )
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'author': User.query.get(session['user_id']).username,
        'text': text,
        'date': datetime.utcnow().strftime('%d.%m.%Y %H:%M')
    })

# [НОВОЕ] Получение комментариев ОРИГИНАЛА
@app.route('/get_pub_comments/<int:pub_id>')
def get_pub_comments(pub_id):
    comments = PublicationComment.query.filter_by(pub_id=pub_id).order_by(PublicationComment.created_at.asc()).all()
    result = []
    for c in comments:
        result.append({
            'author': c.author.username,
            'text': c.text,
            'date': c.created_at.strftime('%d.%m.%Y %H:%M')
        })
    return jsonify({'comments': result})

# --- LIKES ROUTES ---

@app.route('/toggle_pub_like/<int:pub_id>', methods=['POST'])
def toggle_pub_like(pub_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    existing_like = PublicationLike.query.filter_by(pub_id=pub_id, user_id=user_id).first()
    
    if existing_like:
        # Убираем лайк
        db.session.delete(existing_like)
        db.session.commit()
        liked = False
    else:
        # Ставим лайк
        new_like = PublicationLike(pub_id=pub_id, user_id=user_id)
        db.session.add(new_like)
        db.session.commit()
        liked = True
    
    # Подсчитываем общее количество лайков
    like_count = PublicationLike.query.filter_by(pub_id=pub_id).count()
    
    return jsonify({'liked': liked, 'like_count': like_count})

@app.route('/toggle_remix_like/<int:remix_id>', methods=['POST'])
def toggle_remix_like(remix_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    existing_like = RemixLike.query.filter_by(remix_id=remix_id, user_id=user_id).first()
    
    if existing_like:
        # Убираем лайк
        db.session.delete(existing_like)
        db.session.commit()
        liked = False
    else:
        # Ставим лайк
        new_like = RemixLike(remix_id=remix_id, user_id=user_id)
        db.session.add(new_like)
        db.session.commit()
        liked = True
    
    # Подсчитываем общее количество лайков
    like_count = RemixLike.query.filter_by(remix_id=remix_id).count()
    
    return jsonify({'liked': liked, 'like_count': like_count})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')