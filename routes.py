from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, Person, PriceList, Products, Realization, Production, Types, User
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text

def validate_field(column_name, value):
    """Validate field values based on column types."""
    if column_name in ['age', 'quantity']:
        return int(value)
    if column_name in ['name', 'description']:
        return str(value)
    return value

def sanitize_input(value):
    """Prevent SQL injection by escaping dangerous characters."""
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

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                session['username'] = user.username
                flash('Logged in successfully!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password', 'error')
        return render_template('login.html')

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

            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username is already taken', 'error')
                return redirect(url_for('register'))
            # Use the correct hashing method: 'pbkdf2:sha256'
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registered successfully! Please login.', 'success')
            return redirect(url_for('login'))
        return render_template('register.html')

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
                # Handle record deletion
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
                # Handle adding a new record
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

        # Load related data for foreign keys
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
        """Full-text search across tables"""
        if 'username' not in session:
            return redirect(url_for('login'))

        results = None
        query = ""

        if request.method == 'POST':
            table_name = request.form.get('table')
            search_field = request.form.get('search_field')
            search_value = sanitize_input(request.form.get('search_value'))

            models = {
                'Person': Person,
                'Products': Products,
                'Realization': Realization,
                'Production': Production,
                'Types': Types,
                'PriceList': PriceList
            }

            model = models.get(table_name)
            if not model:
                flash("Invalid table selected.", "error")
                return redirect(url_for('search'))

            try:
                query = model.query.filter(getattr(model, search_field).like(f"%{search_value}%"))
                results = query.all()
            except Exception as e:
                flash(f"Search error: {e}", "error")

        return render_template('search.html', results=results, query=query, getattr=getattr)

    @app.route('/execute_query', methods=['POST'])
    def execute_query():
        """Secure execution of custom queries"""
        if 'username' not in session:
            return redirect(url_for('login'))

        allowed_queries = {
            "count_users": "SELECT COUNT(*) FROM user",
            "list_products": "SELECT name, price FROM products LIMIT 10"
        }

        query_key = request.form.get("query_key")

        if query_key not in allowed_queries:
            flash("Unauthorized query request.", "error")
            return redirect(url_for("index"))

        try:
            result = db.session.execute(text(allowed_queries[query_key])).fetchall()
            return render_template("query_results.html", result=result, getattr=getattr)

        except Exception as e:
            flash(f"Query execution error: {e}", "error")
            return redirect(url_for("index"))