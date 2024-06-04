import pika
import json

# เชื่อมต่อ RabbitMQ server
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# ประกาศ Exchange แบบ direct
channel.exchange_declare(exchange='my_exchange', exchange_type='direct')
channel.exchange_declare(exchange='exchange_staff', exchange_type='direct')  # เพิ่มการประกาศ Exchange ของ exchange_staff

# สร้าง queue แบบสุ่มชื่อ
result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue

# Binding queue กับ Exchange
channel.queue_bind(exchange='my_exchange', queue=queue_name, routing_key='my_routing_key')
channel.queue_bind(exchange='exchange_staff', queue=queue_name, routing_key='staff_routing_key')  # เปลี่ยน routing key สำหรับ exchange_staff

print(' [*] Waiting for messages. To exit press CTRL+C')

# กำหนดฟังก์ชัน callback สำหรับการรับข้อความ
def callback(ch, method, properties, body):
    message = json.loads(body)  # แปลงข้อความ JSON เป็น dictionary
    print(" [x] Received %r" % message)

# รับข้อความจาก RabbitMQ
channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

# เริ่มการรับข้อความ
channel.start_consuming()
