from flask import Flask, redirect, render_template, request, url_for
from db_config import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

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
        search_term =f"%{query}%"
        cursor.execute('SELECT * FROM notes WHERE user_id = %s AND (title LIKE %s OR content LIKE %s)', (user_id, search_term, search_term))
    else:
        cursor.execute('SELECT id, title, content, created_at, favourite from notes WHERE user_id = %s', (user_id, ))
    notes = cursor.fetchall()
    conn.close()
    return render_template('index.html', user_name=session['user_name'], notes=notes, query=query, user_id = user_id)

@app.route('/add_note/<int:user_id>', methods = ['POST', 'GET'])
def add_note(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
        
    if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            favourite = 'favourite' in request.form
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO notes (title, content, favourite, user_id) VALUES (%s, %s, %s, %s)', (title, content, favourite, user_id))
            conn.commit()
            conn.close()
            return redirect(f'/index/{user_id}')
    return render_template('add_note.html', user_id = user_id)

@app.route('/delete/<int:note_id>/<int:user_id>', methods =['post'])
def delete_note(note_id, user_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM notes WHERE id = %s AND user_id = %s', (note_id,user_id))
    conn.commit()
    conn.close()

    return redirect(f'/index/{user_id}')

@app.route('/update_note/<int:note_id>/<int:user_id>', methods=['GET', 'POST'])
def update_note(note_id, user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        title = request.form['update_title']
        content = request.form['update_content']
        cursor.execute('UPDATE notes SET title = %s, content = %s WHERE id = %s AND user_id = %s',
                       (title, content, note_id, user_id))
        conn.commit()
        conn.close()
        return redirect(f'/index/{user_id}')

    cursor.execute('SELECT title, content FROM notes WHERE id = %s AND user_id = %s', (note_id, user_id))
    note = cursor.fetchone()
    conn.close()

    return render_template('update_note.html', note=note, note_id=note_id, user_id=user_id)

@app.route('/toggle_button/<int:note_id>/<int:user_id>', methods=['POST'])
def toggle_button(note_id, user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT favourite FROM notes WHERE id = %s AND user_id = %s', (note_id, user_id))
    note = cursor.fetchone()

    if note:
        new_value = not note['favourite']
        cursor.execute('UPDATE notes SET favourite = %s WHERE id = %s AND user_id = %s', (new_value, note_id, user_id))
        conn.commit()

    conn.close()
    return redirect(f'/index/{user_id}')

@app.route('/sign_up', methods=['POST', 'GET'])
def sign_up():
    if request.method == 'POST':
        user_name = request.form['user_name']
        user_pw = request.form['user_pw']
        user_pw_confirm = request.form['user_pw_confirm']

        if user_pw != user_pw_confirm:
            return render_template('sign_up.html', error="Passwords do not match.")
        
        hashed_pw = generate_password_hash(user_pw)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name, password) VALUES (%s, %s)', (user_name, hashed_pw))
        conn.commit()
        conn.close()

        return redirect(url_for('login_page'))

    return render_template('sign_up.html')


@app.route('/login_page', methods=['POST', 'GET'])
def login_page():
    if request.method == "POST":
        user_name = request.form['user_name']
        user_pw = request.form['user_pw']

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE name = %s', (user_name, ))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], user_pw):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('index', user_id=user['id']))
        else:
            return render_template('login.html', error="Invalid username or password.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('user_page'))

if __name__ == '__main__':
    app.run(debug=True)