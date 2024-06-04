from datetime import datetime
from app import db


class User(db.Model):
    __tablename__ = 'user'
    customer_id = db.Column(db.String(100), primary_key=True, nullable=False)
    p_display_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    member_card = db.Column(db.Integer, nullable=False, default=0)
    member_date = db.Column(db.DateTime, nullable=True, default=None)

    def __init__(self, customer_id, p_display_name, customer_phone, member_card=0, member_date=None):
        self.customer_id = customer_id
        self.p_display_name = p_display_name
        self.customer_phone = customer_phone
        self.member_card = member_card
        self.member_date = datetime.now() if member_card else None


class TableNumber(db.Model):
    __tablename__ = 'table_number'
    table_number = db.Column(db.String(10), primary_key=True)
    customer_id = db.Column(db.String(100), db.ForeignKey('user.customer_id'), nullable=True)
    p_display_name = db.Column(db.String(100), nullable=True)
    customer_phone = db.Column(db.String(20), nullable=True)
    table_date = db.Column(db.DateTime, default=None)
    table_status = db.Column(db.Integer, default=0)  # เพิ่ม table_status
    tablecon_status = db.Column(db.Integer, default=0)
    customercon_id = db.Column(db.String(100), nullable=True)
    con_day = db.Column(db.DateTime, default=None)  # เพิ่ม con_day
    pay_status = db.Column(db.Integer, default=0)  # เพิ่ม pay_status
    Grand_Total = db.Column(db.Integer, default=0)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.Integer)
    id_food = db.Column(db.Integer)
    name_food = db.Column(db.String(100))
    price = db.Column(db.Float)
    amount = db.Column(db.Integer)
    total = db.Column(db.Float)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)  # เพิ่มคอลัมน์ order_date
    

    def __init__(self, table_number, id_food, name_food, price, amount, total, order_date):
        self.table_number = table_number
        self.id_food = id_food
        self.name_food = name_food
        self.price = price
        self.amount = amount
        self.total = total
        self.order_date = order_date


    def __repr__(self):
        return f'<Order {self.id_order}>'
    
class Food(db.Model):
    __tablename__ = 'food'

    id_food = db.Column(db.Integer, primary_key=True)
    name_food = db.Column(db.String(100))
    price = db.Column(db.Integer)

    def __init__(self, name_food, price):
        self.name_food = name_food
        self.price = price

class Slip(db.Model):
    __tablename__ = 'slip'

    id_slip = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.Integer)
    slip = db.Column(db.String(100))  # เก็บชื่อไฟล์ slip
    pay_status = db.Column(db.Integer, default=0)  # เพิ่ม pay_status
    slip_date = db.Column(db.DateTime, default=datetime.utcnow)  # เพิ่ม slip_date เพื่อเก็บวันที่
    total_slip = db.Column(db.Integer)  # เพิ่ม total_slip เพื่อเก็บจำนวนเงิน

    def __init__(self, table_number, slip, pay_status, slip_date, total_slip):
        self.table_number = table_number
        self.slip = slip
        self.pay_status = pay_status
        self.slip_date = slip_date
        self.total_slip = total_slip
