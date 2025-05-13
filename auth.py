from flask import Blueprint, request, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from models import User
from extensions import db

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')


@auth_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')  # Получаем username
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('Username, Email, and Password are required.', 'error')
            return redirect(url_for('auth.register'))

        # Проверка, существует ли уже пользователь с таким email
        if User.query.filter_by(email=email).first():
            flash('Email is already in use.', 'error')
            return redirect(url_for('auth.register'))

        # Генерация хешированного пароля
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

        # Создание нового пользователя
        new_user = User(username=username, email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))