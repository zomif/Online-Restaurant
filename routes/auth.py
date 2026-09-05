from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

auth = Blueprint('auth', __name__)

users_db = {}

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        if email in users_db:
            flash('Email is already registered.', 'error')
            return render_template('register.html')

        hashed_password = generate_password_hash(password, method='scrypt')
        users_db[email] = {
            'username': username,
            'password': hashed_password
        }

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = users_db.get(email)

        if not user or not check_password_hash(user['password'], password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html')

        session['user_email'] = email
        session['username'] = user['username']

        flash('Logged in successfully!', 'success')
        return redirect(url_for('main.index'))

    return render_template('login.html')


@auth.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
