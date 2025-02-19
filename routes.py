﻿from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, Person, PriceList, Products, Realization, Production, Types, User
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text, or_, and_

def validate_field(column_name, value):
    if column_name in ['age', 'quantity']:
        return int(value)
    if column_name in ['name', 'description']:
        return str(value)
    return value

def sanitize_input(value):
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "xp_"]
    for char in dangerous_chars:
        value = value.replace(char, "")
    return value

def register_routes(app, db):
    @app.route('/')
    def index():
        if 'username' in session:
            tables = ['Person', 'PriceList', 'Products', 'Realization', 'Production', 'Types', 'User']
            return render_template('index.html', tables=tables)
        return redirect(url_for('login'))

    import pymysql

    ADMIN_USER = "root"
    ADMIN_PASSWORD = "Valik25122005!"
    DB_HOST = "127.0.0.1"
    DB_NAME = "flask_db"

    # Функція для підключення до БД як адміністратор
    def get_admin_connection():
        return pymysql.connect(
            host=DB_HOST,
            user=ADMIN_USER,
            password=ADMIN_PASSWORD,
            database=DB_NAME
        )

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return redirect(url_for('register'))

            admin_conn = None
            try:
                # Підключення до MySQL як адміністратор
                admin_conn = get_admin_connection()
                with admin_conn.cursor() as cursor:
                    # Перевірка, чи email вже існує
                    cursor.execute("SELECT id FROM User WHERE email = %s", (email,))
                    if cursor.fetchone():
                        flash('Email already registered', 'error')
                        return redirect(url_for('register'))

                    # Створення користувача у MySQL
                    cursor.execute(f"CREATE USER '{username}'@'%' IDENTIFIED BY '{password}';")
                    cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {DB_NAME}.* TO '{username}'@'%';")

                    # Хешування паролю для збереження у таблиці User
                    hashed_password = generate_password_hash(password)

                    # Додавання користувача у таблицю User
                    cursor.execute("INSERT INTO User (username, email, password) VALUES (%s, %s, %s)",
                                   (username, email, hashed_password))
                    admin_conn.commit()

                flash('User registered successfully! You can now log in.', 'success')
                return redirect(url_for('login'))

            except pymysql.MySQLError as e:
                flash(f'Error creating MySQL user: {e}', 'error')

            finally:
                if admin_conn:
                    admin_conn.close()

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            admin_conn = None
            try:
                # Перевірка пароля у таблиці User
                admin_conn = get_admin_connection()
                with admin_conn.cursor() as cursor:
                    cursor.execute("SELECT password FROM User WHERE username = %s", (username,))
                    user_data = cursor.fetchone()

                    if not user_data or not check_password_hash(user_data[0], password):
                        flash('Invalid username or password', 'error')
                        return redirect(url_for('login'))

                # Якщо пароль правильний, підключаємося до MySQL як користувач
                user_conn = pymysql.connect(
                    host=DB_HOST,
                    user=username,
                    password=password,
                    database=DB_NAME
                )
                user_conn.close()

                session['username'] = username
                flash('Logged in successfully!', 'success')
                return redirect(url_for('index'))

            except pymysql.MySQLError:
                flash('Invalid username or password', 'error')

            finally:
                if admin_conn:
                    admin_conn.close()

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.pop('username', None)
        flash('Logged out successfully!', 'success')
        return redirect(url_for('login'))

    @app.route('/table/<table_name>', methods=['GET', 'POST'])
    def view_table(table_name):
        if 'username' not in session:
            return redirect(url_for('login'))
        models = {
            'Person': Person,
            'PriceList': PriceList,
            'Products': Products,
            'Realization': Realization,
            'Production': Production,
            'Types': Types,
            'User': User
        }
        model = models.get(table_name)
        if not model:
            return f"No table named {table_name}", 404

        if request.method == 'POST':
            if 'delete_id' in request.form:
                delete_id = request.form['delete_id']
                try:
                    record = model.query.get(delete_id)
                    if record:
                        db.session.delete(record)
                        db.session.commit()
                        flash('Record deleted successfully!', 'success')
                    else:
                        flash('Record not found!', 'error')
                except Exception as e:
                    flash(f'Error deleting record: {e}', 'error')
            else:
                data = request.form
                try:
                    validated_data = {key: validate_field(key, value) for key, value in data.items() if key != 'delete_id'}
                    new_record = model(**validated_data)
                    db.session.add(new_record)
                    db.session.commit()
                    flash('Record added successfully!', 'success')
                except Exception as e:
                    flash(f'Error: {e}', 'error')
            return redirect(url_for('view_table', table_name=table_name))

        rows = model.query.all()
        columns = [column.name for column in model.__table__.columns]

        related_data = {}

        return render_template(
            'table.html',
            table_name=table_name,
            rows=rows,
            columns=columns,
            related_items=related_data,
            getattr=getattr
        )

    @app.route('/table/<table_name>/edit/<int:record_id>', methods=['GET', 'POST'])
    def edit_record(table_name, record_id):
        if 'username' not in session:
            return redirect(url_for('login'))
        models = {
            'Person': Person,
            'PriceList': PriceList,
            'Products': Products,
            'Realization': Realization,
            'Production': Production,
            'Types': Types,
            'User': User
        }
        model = models.get(table_name)
        if not model:
            return f"No table named {table_name}", 404

        record = model.query.get(record_id)
        if not record:
            return f"Record with ID {record_id} not found in {table_name}", 404

        if request.method == 'POST':
            try:
                # Update data
                for key, value in request.form.items():
                    if key in record.__table__.columns:
                        setattr(record, key, validate_field(key, value))
                db.session.commit()
                flash('Record updated successfully!', 'success')
            except Exception as e:
                flash(f'Error updating record: {e}', 'error')
            return redirect(url_for('view_table', table_name=table_name))

        columns = [column.name for column in model.__table__.columns]

        return render_template(
            'edit_record.html',
            table_name=table_name,
            record=record,
            columns=columns,
            getattr=getattr
        )

    @app.route('/search', methods=['GET', 'POST'])
    def search():
        if 'username' not in session:
            return redirect(url_for('login'))

        results = None
        query_str = ""
        mode = "normal"

        if request.method == 'POST':
            table_name = request.form.get('table')
            search_field = request.form.get('search_field')
            search_value = request.form.get('search_value')
            mode = request.form.get('search_mode')

            models = {'Person': Person, 'Products': Products, 'Realization': Realization, 'Production': Production,
                      'Types': Types, 'PriceList': PriceList}
            model = models.get(table_name)

            if not model:
                flash("Невірна таблиця.", "error")
                return redirect(url_for('search'))

            try:
                if mode == "normal":
                    query_str = model.query.filter(getattr(model, search_field).like(f"%{search_value}%"))
                elif mode == "logical_OR":
                    search_fields = request.form.getlist('search_field')
                    search_values = request.form.getlist('search_value')

                    conditions = [
                        getattr(model, field).like(f"{value}")
                        for field, value in zip(search_fields, search_values)
                    ]

                    query_str = model.query.filter(or_(*conditions))

                elif mode == "logical_AND":
                    search_fields = request.form.getlist('search_field')
                    search_values = request.form.getlist('search_value')

                    conditions = [
                        getattr(model, field).like(f"%{value}%")
                        for field, value in zip(search_fields, search_values)
                    ]

                    query_str = model.query.filter(and_(*conditions))

                elif mode == "extended":
                    fields = [col.name for col in model.__table__.columns]
                    query_str = model.query.filter(
                        db.or_(*[getattr(model, field).like(f"%{search_value}%") for field in fields])
                    )

                results = query_str.all()
            except Exception as e:
                flash(f"Помилка пошуку: {e}", "error")

        stored_procedures = ['update_statistics', 'recalculate_prices', 'archive_old_data']
        return render_template('search.html', results=results, query=query_str, stored_procedures=stored_procedures,
                               mode=mode, getattr=getattr)


    @app.route('/execute_procedure', methods=['POST'])
    def execute_procedure():
        if 'username' not in session:
            return redirect(url_for('login'))

        proc_name = request.form.get('procedure')
        param_value = request.form.get('procedure_param')

        try:
            with db.session.begin():
                if param_value:
                    result = db.session.execute(
                        text(f"CALL {proc_name}(:param)"), {"param": param_value}
                    )
                else:
                    result = db.session.execute(text(f"CALL {proc_name}()"))

                rows = result.fetchall()
                columns = result.keys() if rows else []

            return render_template('procedure_results.html', results=rows, columns=columns, getattr=getattr)
        except Exception as e:
            flash(f'Error of executing procedures {proc_name}: {e}', 'error')
            return redirect(url_for('search'))





