from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from app import app, db
from app.models import TableNumber, User
import time
import requests
import json


def reset_table_status_15_hours():
    now = datetime.utcnow()
    # กำหนดเวลา 15:00 ของวันนั้น
    reset_time = now.replace(hour=15, minute=0, second=0, microsecond=0)
    
    # ตรวจสอบว่าเวลาปัจจุบันมากกว่าหรือเท่ากับเวลาที่ต้องการรีเซ็ต
    if now >= reset_time:
        # คำนวณเวลาที่ต้องการที่โต๊ะจะถูกรีเซ็ต โดยเพิ่ม 11 ชั่วโมง
        cutoff_time = reset_time + timedelta(hours=11)
        
        # ค้นหาโต๊ะที่ต้องการรีเซ็ตสถานะ
        tables_to_reset = TableNumber.query.filter(TableNumber.table_status == 1).all()
        
        # ตรวจสอบและรีเซ็ตสถานะของโต๊ะ
        for table in tables_to_reset:
            if table.table_date and now >= cutoff_time:
                table.customer_id = None
                table.p_display_name = None
                table.customer_phone = None
                table.table_status = 0
                table.table_date = None
                table.pay_status = 0
        
        db.session.commit()

def reset_table_status_25_hours():
    now = datetime.utcnow()
    
    # กำหนดเวลาสิ้นสุดของช่วงเวลาที่ต้องการให้รีเซ็ต
    cutoff_time = now - timedelta(hours=25)
    
    # ค้นหาโต๊ะที่ต้องการรีเซ็ตสถานะ
    tables_to_reset = TableNumber.query.filter(
        TableNumber.con_day == now.date(),  # ตรวจสอบว่าเป็นวันเดียวกันหรือไม่
        TableNumber.table_status == 1
    ).all()
    
    # ตรวจสอบและรีเซ็ตสถานะของโต๊ะ
    for table in tables_to_reset:
        # ตรวจสอบเงื่อนไขวันที่ก่อนทำการนับถอยหลัง
        if table.con_day == now.date() and table.table_date < cutoff_time:
            table.customer_id = None
            table.p_display_name = None
            table.customer_phone = None
            table.table_status = 0
            table.table_date = None
            table.pay_status = 0
            table.tablecon_status = 0
            table.customercon_id = None
            table.con_day = None
    
    db.session.commit()


def send_reminder_message():
    now = datetime.utcnow()
    
    # ตรวจสอบว่าเวลาปัจจุบันเป็น 20:30 หรือไม่
    if now.hour == 20 and now.minute == 30:
        # ค้นหาโต๊ะที่ต้องการแจ้งเตือน
        tables_to_remind = TableNumber.query.filter(
            TableNumber.table_status == 1,
            TableNumber.table_date != None
        ).all()
        
        # ส่งข้อความแจ้งเตือนถึงผู้ใช้
        for table in tables_to_remind:
            user = User.query.filter_by(customer_id=table.customer_id).first()
            if user:
                send_message(user.customer_id, table.table_number)

                # ฟังก์ชันสำหรับส่งข้อความแจ้งเตือนผู้ใช้
    

# ฟังก์ชันสำหรับส่งข้อความแจ้งเตือนถึงผู้ใช้
def send_message(customer_id, table_number):
    message = f"อย่าลืมมาเอาโต๊ะหมายเลข {table_number} ก่อน 20.30 นะครับ"
    
    # สร้าง payload สำหรับการส่งข้อความ
    payload = {
        "to": customer_id,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    
    # ส่ง request ไปยัง Messaging API endpoint ของ LINE
    headers = {
        "Authorization": "pNUj5DTHmGae5RJAvX634Qwgh8shE5TFqudxLxrbnKU4g3vDJyU4gLpCyCzc76yRJPB5OnB695Ss1BPFXpFJKB9Ydv/C3Svmsogu9KEbiPSj5LyR0Z3P+mJ5yd/A9tKjYAERGDmiFoSzxWhkrjVjOgdB04t89/1O/w1cDnyilFU=",
        "Content-Type": "application/json"
    }
    
    api_url = "https://api.line.me/v2/bot/message/push"
    response = requests.post(api_url, headers=headers, json=payload)
    
    if response.status_code == 200:
        print(f"Message sent successfully to {customer_id}: {message}")
    else:
        print(f"Failed to send message to {customer_id}: {response.text}")

# เรียกใช้งานฟังก์ชันส่งข้อความแจ้งเตือน
send_reminder_message()



def send_reminder_messages():
    now = datetime.utcnow()
    
    # ตรวจสอบว่าเวลาปัจจุบันเป็น 20:30 หรือไม่
    if now.hour == 20 and now.minute == 30:
        # ค้นหาโต๊ะที่มีสถานะเป็น 0 (ว่าง) ในตาราง TableNumber
        available_tables = TableNumber.query.filter(TableNumber.table_status == 0).all()
        
        # ถ้ามีโต๊ะว่าง
        if available_tables:
            # ค้นหา customer_id ที่ไม่มีข้อมูลในตาราง TableNumber
            users_to_notify = User.query.outerjoin(TableNumber, User.customer_id == TableNumber.customer_id).filter(TableNumber.customer_id == None).all()
            
            # สร้างข้อความที่รวมหมายเลขโต๊ะที่ว่างมาด้วยกัน
            message = "โต๊ะว่างอยู่ รีบมาจองค่ะ/ครับ\n"
            message += "หมายเลขโต๊ะที่ว่าง: " + ", ".join(str(table.table_number) for table in available_tables)
            
            # ส่งข้อความแจ้งเตือนผู้ใช้
            for user in users_to_notify:
                send_messages(user.customer_id, message)
                
            print("Sent availability notifications successfully.")


def send_messages(customer_id, message):
    # สร้าง payload สำหรับการส่งข้อความ
    payload = {
        "to": customer_id,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    
    # ส่ง request ไปยัง Messaging API endpoint ของ LINE
    headers = {
        "Authorization": "pNUj5DTHmGae5RJAvX634Qwgh8shE5TFqudxLxrbnKU4g3vDJyU4gLpCyCzc76yRJPB5OnB695Ss1BPFXpFJKB9Ydv/C3Svmsogu9KEbiPSj5LyR0Z3P+mJ5yd/A9tKjYAERGDmiFoSzxWhkrjVjOgdB04t89/1O/w1cDnyilFU=",
        "Content-Type": "application/json"
    }
    
    api_url = "https://api.line.me/v2/bot/message/push"
    response = requests.post(api_url, headers=headers, json=payload)
    
    if response.status_code == 200:
        print(f"Message sent successfully to {customer_id}: {message}")
    else:
        print(f"Failed to send message to {customer_id}: {response.text}")

# เรียกใช้งานฟังก์ชันส่งข้อความแจ้งเตือน
send_reminder_messages()

# ตั้งค่า Scheduler สำหรับรันงานตามเวลาที่กำหนด
scheduler = BackgroundScheduler(timezone=pytz.utc)
scheduler.add_job(func=reset_table_status_15_hours, trigger='interval', hours=15)
scheduler.add_job(func=reset_table_status_25_hours, trigger='interval', hours=25)
scheduler.add_job(func=send_reminder_message, trigger=CronTrigger(hour=20, minute=0))
scheduler.add_job(func=send_reminder_messages,trigger=CronTrigger(hour=20, minute=30))
scheduler.start()

@app.teardown_appcontext
def shutdown_scheduler(exception=None):
    if scheduler.running:
        scheduler.shutdown()
