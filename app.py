from flask import Flask, redirect, render_template, request, url_for
from db_config import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = 'abc123$!@'

@app.route('/')
def user_page():
    return render_template('user_page.html')

@app.route('/index/<int:user_id>')
def index(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    query = request.args.get('query')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    if query:
        search_term = f"%{query}%"
        cursor.execute('''
    SELECT products.*, users.username AS author_name
    FROM products
    JOIN users ON products.user_id = users.id
    WHERE title LIKE %s OR description LIKE %s
''', (search_term, search_term))
    else:
        cursor.execute('''
    SELECT products.*, users.username AS author_name
    FROM products
    JOIN users ON products.user_id = users.id
''')
    
    products = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', user_name=session['user_name'], user_email=session['user_email'], products=products, query=query, user_id=user_id)

@app.route('/user_profile/<int:user_id>')
def user_profile(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    query = request.args.get('query')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    if query:
        search_term = f"%{query}%"
        cursor.execute('''
            SELECT * FROM products 
            WHERE user_id = %s AND (title LIKE %s OR description LIKE %s)
        ''', (user_id, search_term, search_term))
    else:
        cursor.execute('SELECT * FROM products WHERE user_id = %s', (user_id,))
    
    products = cursor.fetchall()
    conn.close()
    
    return render_template('user_profile.html', user_email=session['user_email'], products=products, query=query, user_id=user_id)


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/add_product/<int:user_id>', methods=['GET', 'POST'])
def add_product(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        image_file = request.files['image']

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO products (user_id, title, description, price, image_filename)
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, title, description, price, filename))
            conn.commit()
            conn.close()
            return redirect(f'/index/{user_id}')
        else:
            return "Invalid file type. Only images allowed."

    return render_template('add_product.html', user_id=user_id)

@app.route('/delete/<int:note_id>/<int:user_id>', methods=['POST'])
def delete_product(note_id, user_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = %s AND user_id = %s', (note_id, user_id))
    conn.commit()
    conn.close()

    return redirect(f'/user_profile/{user_id}')

@app.route('/sign_up', methods=['POST', 'GET'])
def sign_up():
    if request.method == 'POST':
        user_name = request.form['user_name']
        user_email = request.form.get('user_email')
        user_pw = request.form['user_pw']
        user_pw_confirm = request.form['user_pw_confirm']

        if user_pw != user_pw_confirm:
            return render_template('sign_up.html', error="Passwords do not match.")
        
        hashed_pw = generate_password_hash(user_pw)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', (user_name, user_email, hashed_pw))
        conn.commit()
        conn.close()

        return redirect(url_for('login_page'))

    return render_template('sign_up.html')


@app.route('/login_page', methods=['POST', 'GET'])
def login_page():
    if request.method == "POST":
        user_email = request.form['user_email']
        user_pw = request.form['user_pw']

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (user_email, ))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], user_pw):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['username']
            return redirect(url_for('index', user_id=user['id']))
        else:
            return render_template('login.html', error="Invalid email or password.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('user_page'))

if __name__ == '__main__':
    app.run(debug=True)