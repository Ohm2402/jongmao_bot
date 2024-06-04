from app import db
from app.models import Food

# ฟังก์ชันสำหรับเพิ่มข้อมูลในตาราง Food
def populate_food_table():
    food_items = [
        {"name_food": "ช้าง", "price": 75.00},
        {"name_food": "สิง", "price": 85.00},
        {"name_food": "แสงโสม", "price": 350.00},
        {"name_food": "เบน285", "price": 330.00},
        {"name_food": "หงทอง", "price": 370.00},
        {"name_food": "โซดา", "price": 35.00},
        {"name_food": "โค้ก", "price": 35.00},
        {"name_food": "น้ำเปล่า", "price": 35.00},
        {"name_food": "น้ำแข็ง", "price": 30.00}
    ]
# s
    for item in food_items:
        # เช็คว่ามีข้อมูลอยู่แล้วหรือไม่
        existing_food = Food.query.filter_by(name_food=item['name_food']).first()
        if not existing_food:
            food = Food(name_food=item['name_food'], price=item['price'])
            db.session.add(food)

    db.session.commit()

# เรียกใช้ฟังก์ชันเพื่อเพิ่มข้อมูล
populate_food_table()
