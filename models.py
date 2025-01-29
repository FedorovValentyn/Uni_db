from app import db


class Person(db.Model):
    __tablename__ = 'person'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    job = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return '<Person %r>' % self.name


class PriceList(db.Model):
    __tablename__ = 'price_list'

    id = db.Column(db.Integer, primary_key=True)
    price_list_id_prod = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    price_list_id_type = db.Column(db.Integer, db.ForeignKey('types.id'), nullable=False)
    price_list_price = db.Column(db.DECIMAL(8, 2), nullable=False)

    product = db.relationship('Products', backref='price_lists')
    type = db.relationship('Types', backref='price_lists')


    def __repr__(self):
        return f'id {self.id}, id_prod{self.price_list_id_prod}, id_type {self.price_list_id_type}, price{self.price_list_price}'


class Products(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    prod_name = db.Column(db.String(80), nullable=False)


    def __repr__(self):
        return f'id {self.id}, name {self.prod_name}'


class Realization(db.Model):
    __tablename__ = 'realization'

    id = db.Column(db.Integer, primary_key=True)
    realization_name = db.Column(db.String(35), nullable=False)
    realization_surname = db.Column(db.String(35), nullable=False)
    realization_middle_name = db.Column(db.String(35), nullable=False)


    def __repr__(self):
        return f'id {self.id}, name {self.realization_name}, surname {self.realization_surname}, middle_name {self.realization_middle_name}'


class Production(db.Model):
    __tablename__ = 'production'

    production_id = db.Column(db.Integer, db.ForeignKey('realization.id'), nullable=False)
    production_price_list_id = db.Column(db.Integer, db.ForeignKey('price_list.id'), nullable=False)
    production_quantity = db.Column(db.Integer, nullable=False)
    production_date = db.Column(db.Date, nullable=False)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    realization = db.relationship('Realization', backref='productions')
    price_list = db.relationship('PriceList', backref='productions')


    def __repr__(self):
        return f'id {self.production_id} price_list_id {self.production_price_list_id}, quantity {self.production_quantity}, date {self.production_date}, un_id {self.id}'



class Types(db.Model):
    __tablename__ = 'types'

    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(80), nullable=False)


    def __repr__(self):
        return f'id {self.id}, name {self.type_name}'


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(200), nullable=False)


    def __repr__(self):
        return f'id {self.id}, username {self.username}, email {self.email}'