from app import app
import json
import pika
from app.models import db, Order  # แก้ไขการ import โมเดล Order
from datetime import datetime
from flask import request
from pytz import timezone

# เรียกพนักงาน
def send_staff(table_number):
    # เชื่อมต่อไปยัง RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # ส่งข้อมูล table_number ไปยัง Exchange ที่ชื่อ 'exchange_staff'
    channel.exchange_declare(exchange='exchange_staff', exchange_type='direct')

    # สร้างข้อความที่จะส่งไปยัง RabbitMQ โดยแปลงข้อมูลเป็นรูปแบบ JSON string
    message = {'message': f'ตอนนี้โต๊ะ {table_number} เรียกพนักงาน'}
    message_str = json.dumps(message)

    # ส่งข้อมูล table_number ไปยัง Exchange ที่ชื่อ 'exchange_staff' โดยใช้ 'staff_routing_key' เป็น routing key
    channel.basic_publish(exchange='exchange_staff', routing_key='staff_routing_key', body=message_str)
    print(" [x] Sent 'Table Number: %s'" % table_number)

    connection.close()



# ส่งออเดอร์
def send_to_rabbitmq(order_id, table_number, id_food, name_food, price, amount, total, order_date):  
    thai_timezone = timezone('Asia/Bangkok')
    # เพิ่มการเช็ควันที่ปัจจุบัน
    current_date = datetime.now(thai_timezone).date()
    
    # ตรวจสอบว่าวันที่ใน order_date เท่ากับวันที่ปัจจุบันหรือไม่
    if order_date.date() == current_date:
        # ตั้งค่าการเชื่อมต่อกับ RabbitMQ
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()

        # สร้าง Exchange ชื่อ 'user_created_exchange' แบบ direct
        channel.exchange_declare(exchange='user_created_exchange', exchange_type='direct')

        # สร้างข้อความที่จะส่งไปยัง RabbitMQ โดยแปลงข้อมูลเป็นรูปแบบ JSON string
        message = {
            'order_id': order_id,
            'table_number': table_number,
            'id_food': id_food,
            'name_food': name_food,
            'price': price,
            'amount': amount,
            'total': total,
            'order_date': str(order_date)  # แปลงวันที่เป็น string เพื่อให้ JSON serializable
        }

        # ตรวจสอบและแปลงข้อมูลประเภท bytes เป็น string (ถ้ามี)
        for key, value in message.items():
            if isinstance(value, bytes):
                message[key] = value.decode('utf-8')

        message_str = json.dumps(message)  # แปลง dictionary เป็น JSON string

        # ส่งข้อความไปยัง Exchange
        channel.basic_publish(exchange='my_exchange', routing_key='my_routing_key', body=message_str)
        print(f" [x] Sent '{message_str}'")

        # ปิดการเชื่อมต่อ
        connection.close()

        # Return ข้อความเป็น text
        return f"Sent message to RabbitMQ: {message_str}"
    else:
        # ถ้าไม่ตรงกับวันที่ปัจจุบัน ไม่ส่งข้อมูล
        print("Order date is not current date. Skipping sending data to RabbitMQ.")
        return "Order date is not current date. Skipping sending data to RabbitMQ."

# ฟังก์ชันสำหรับ query ข้อมูลการจองทั้งหมดจากฐานข้อมูล
def query_all_order_data():
    orders = db.session.query(Order).all()  
    order_data_list = []
    for order in orders:
        order_data = {
            'order_id': order.id,
            'table_number': order.table_number,
            'id_food': order.id_food,
            'name_food': order.name_food,
            'price': order.price,
            'amount': order.amount,
            'total': order.total,
            'order_date': order.order_date
        }
        for key, value in order_data.items():
            if isinstance(value, bytes):
                order_data[key] = value.decode('utf-8')
        order_data_list.append(order_data)
    return order_data_list

if __name__ == "__main__":
    from app import app  

    with app.app_context():
        order_data_list = query_all_order_data()  
        if order_data_list:
            for order_data in order_data_list:
                response = send_to_rabbitmq(**order_data)  
                print(response)

        else:
            print("ไม่พบข้อมูลการจองในฐานข้อมูล")
