import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy import text  # เพิ่มการนำเข้า text
# Initialize app
app = Flask(__name__)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(basedir, '../database')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(db_dir, 'User_information.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)
ma = Marshmallow(app)

# Import routes and scheduler to register them
from app import routes, scheduler
from app.routes import populate_table_numbers

# สร้างตารางและเพิ่มข้อมูลเลขโต๊ะเมื่อแอปพลิเคชันเริ่มทำงาน
with app.app_context():
    db.create_all()  # สร้างตารางในฐานข้อมูลถ้ายังไม่มี
    populate_table_numbers()  # เรียกฟังก์ชัน populate_table_numbers เพื่อเพิ่มข้อมูลเลขโต๊ะ
    db.session.commit()  # บันทึกการเปลี่ยนแปลง

# ทดสอบการเชื่อมต่อกับฐานข้อมูล
try:
    with app.app_context():
        # ใช้ text() เพื่อระบุคอลัมน์ '1' อย่างชัดเจน
        db.session.query(text('1')).from_statement(text('SELECT 1')).all()
    print("Connected to the database successfully!")
except Exception as e:
    print(f"Database connection error: {e}")
