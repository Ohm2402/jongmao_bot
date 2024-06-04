from flask import request, jsonify , Response
from app import app, db
from app.models import User, TableNumber, Food, Order, Slip
from app.schemas import user_schema, orders_schema, table_number_schema, table_numbers_schema
from datetime import datetime,date
from app.scheduler import shutdown_scheduler
from app.encryption import encrypt_data, decrypt_data
from producer import send_to_rabbitmq ,send_staff
from pytz import timezone

# กำหนดเขตเวลาของไทย
thai_timezone = timezone('Asia/Bangkok')

# โหลดคีย์จากไฟล์
def load_key():
    return open('secret.key', 'rb').read()

key = load_key()

# บันทึกข้อมูลผู้ใช้
@app.route('/user', methods=['POST'])
def add_user():
    try:
        # ดึงข้อมูลที่ส่งมาจากผู้ใช้ผ่านทาง URL query parameters
        customer_id = request.args.get('customer_id')
        p_display_name = request.args.get('p_display_name')
        customer_phone = request.args.get('customer_phone')

        # ตรวจสอบว่าข้อมูลที่จำเป็นทั้งหมดถูกส่งมาครบถ้วนหรือไม่
        if not customer_id or not p_display_name or not customer_phone:
            return jsonify({"error": "กรุณากรอกข้อมูลให้ครบถ้วน"}), 400

        # เช็คว่ามีข้อมูล customer_id ในฐานข้อมูลหรือไม่
        existing_user = User.query.filter_by(customer_id=customer_id).first()
        if (existing_user):
            return jsonify({"message": "ตอนนี้เรามีข้อมูลของลูกค้าเรียบร้อยแล้ว"}), 200

        # เข้ารหัสหมายเลขโทรศัพท์ของลูกค้า
        encrypted_customer_phone = encrypt_data(customer_phone, key)

        # สร้าง instance ใหม่ของโมเดล User โดยใช้ข้อมูลที่ได้รับมา (รวมกับหมายเลขโทรศัพท์ที่เข้ารหัสแล้ว)
        new_user = User(customer_id=customer_id, p_display_name=p_display_name, customer_phone=encrypted_customer_phone)
        # เพิ่มข้อมูลผู้ใช้ใหม่ลงใน session ของฐานข้อมูล
        db.session.add(new_user)
        # บันทึกการเปลี่ยนแปลงลงในฐานข้อมูล
        db.session.commit()
        # ส่งข้อความทำการบันทึกข้อมูลเสร็จสิ้นกลับไปหาผู้ใช้
        return jsonify({"message": "ทำการบันทึกข้อมูลเสร็จสิ้น"}), 201
    except Exception as e:
        # ถ้ามีข้อผิดพลาดเกิดขึ้น ให้พิมพ์ข้อผิดพลาดลงใน console
        print(f"Error: {e}")
        # ส่งข้อความข้อผิดพลาดกลับไปยังผู้ใช้ในรูปแบบ JSON
        return jsonify({"error": "เกิดข้อผิดพลาดในการบันทึกข้อมูลผู้ใช้"}), 500

# เช็คข้อมูลผู้ใช้
@app.route('/get_user', methods=['GET'])
def get_user():
    customer_id = request.args.get('customer_id')

    # ค้นหาผู้ใช้ตาม customer_id
    user = User.query.filter_by(customer_id=customer_id).first()

    if user:
        if user.member_card == 0:
            message = "ยังไม่ได้ทำการสมัครสมาชิก"
            member_date_info = "ยังไม่ได้ทำการสมัครสมาชิก"
        else:
            message = "สมัครสมาชิกแล้ว"
            member_date_info = user.member_date.strftime('%Y-%m-%d') if user.member_date else "ยังไม่ได้ทำการสมัครสมาชิก"

        # ถอดรหัส customer_phone
        try:
            decrypted_phone = decrypt_data(user.customer_phone, key)
        except Exception as e:
            print(f"Decryption error: {e}")
            return Response("การถอดรหัสข้อมูลล้มเหลว", status=500, mimetype='text/plain')

        # สร้างข้อความตอบกลับ
        response_text = f"ชื่อ: {user.p_display_name}\nเบอร์โทร: {decrypted_phone}\nสมัครสมาชิก: {message}\nวันที่สมัคร: {member_date_info}"
        return Response(response_text, status=200, mimetype='text/plain')

    else:
        return Response("ไม่พบข้อมูล", status=404, mimetype='text/plain')

# _____________________________________________________________________________________________________________________

# เช็คโต๊ะ
@app.route('/Ctable', methods=['GET'])
def Ctable():
 # ดึงข้อมูลโต๊ะทั้งหมดจากฐานข้อมูล
    tables = TableNumber.query.all()
    
    # สร้างรายการโต๊ะที่ว่าง โดยตรวจสอบว่า table_status เท่ากับ 0 (โต๊ะว่าง)
    available_tables = [table.table_number for table in tables if table.table_status == 0]
    # ตรวจสอบว่ามีโต๊ะว่างหรือไม่
    if not available_tables:
        # ถ้าไม่มีโต๊ะว่าง ส่งข้อความ "ตอนนี้โต๊ะเต็มหมดแล้ว"
        return "ตอนนี้โต๊ะเต็มหมดแล้ว"
    
    if available_tables:
        # ถ้ามีโต๊ะว่าง ส่งข้อความพร้อมรายการโต๊ะว่างกลับไป
        return "โต๊ะที่ว่างอยู่ในตอนนี้\n" + "\t".join(available_tables)
    


@app.route('/reserve_table', methods=['POST'])
def reserve_table():
    # รับค่า table_number และ customer_id จากพารามิเตอร์ใน URL ของคำขอ
    table_number = request.args.get('table_number')
    customer_id = request.args.get('customer_id')

    # ตรวจสอบว่าโต๊ะมีอยู่ในฐานข้อมูลหรือไม่
    table = TableNumber.query.filter_by(table_number=table_number).first()
    if not table:
        # ถ้าไม่พบโต๊ะที่ตรงกับ table_number จะส่งข้อความแสดงข้อผิดพลาดกลับไป
        return Response("กรุณาเลือกโต๊ะที่ต้องการใหม่อีกครั้ง", status=400, mimetype='text/plain')

    # ตรวจสอบว่าโต๊ะถูกจองแล้วหรือไม่
    if table.table_status == 1:
        # ถ้าโต๊ะถูกจองแล้ว จะส่งข้อความแสดงข้อผิดพลาดกลับไปในรูปแบบ text
        return Response("ตอนนี้โต๊ะที่ท่านเลือกได้ถูกจองแล้ว กรุณาเลือกโต๊ะใหม่", status=400, mimetype='text/plain')

    # ตรวจสอบว่าผู้ใช้มีอยู่ในฐานข้อมูลหรือไม่
    user = User.query.filter_by(customer_id=customer_id).first()
    if not user:
        # ถ้าไม่พบผู้ใช้ จะส่งข้อความแสดงข้อผิดพลาดกลับไปในรูปแบบ text
        return Response("ผู้ใช้ไม่พบ", status=404, mimetype='text/plain')

    # แปลงเวลาปัจจุบันเป็นเวลาของไทย
    thai_time = datetime.now(thai_timezone)

    # อัปเดตข้อมูลโต๊ะ
    table.customer_id = customer_id
    table.p_display_name = user.p_display_name
    table.customer_phone = user.customer_phone
    table.table_status = 1
    table.table_date = thai_time  # บันทึกเวลาที่อัปเดตในรูปแบบของไทย

    # บันทึกการเปลี่ยนแปลงลงในฐานข้อมูล
    db.session.commit()

    confirmation_message = f"ยืนยันการจอง\nหมายเลขโต๊ะ: {table.table_number}\nมาเอาโต๊ะก่อน 20.30 นะครับ"

    return Response(confirmation_message, status=200, mimetype='text/plain')




# _____________________________________________________________________________________________________________________
# เช็คโต๊ะคอน
@app.route('/Ctablecon', methods=['GET'])
def Ctablecon():
 # ดึงข้อมูลโต๊ะทั้งหมดจากฐานข้อมูล
    tables = TableNumber.query.all()
    # ตรวจสอบว่ามีโต๊ะที่มีข้อมูลใน con_day หรือไม่
    tables_with_con_day = [table for table in tables if table.con_day is not None]

    # ถ้าไม่มีโต๊ะที่มีข้อมูลใน con_day
    if not tables_with_con_day:
        # ส่งข้อความแจ้งเตือนว่ายังไม่มีข้อมูลใน con_day
        return "ตอนนี้ยังไม่มีคอน"
    # สร้างรายการโต๊ะที่ว่าง โดยตรวจสอบว่า table_status เท่ากับ 0 (โต๊ะว่าง)
    available_tables = [table.table_number for table in tables if table.tablecon_status == 0]
    # ตรวจสอบว่ามีโต๊ะว่างหรือไม่
    if not available_tables:
        # ถ้าไม่มีโต๊ะว่าง ส่งข้อความ "ตอนนี้โต๊ะเต็มหมดแล้ว"
        return "ตอนนี้โต๊ะเต็มหมดแล้ว"
    
    if available_tables:
        # ถ้ามีโต๊ะว่าง ส่งข้อความพร้อมรายการโต๊ะว่างกลับไป
        return "โต๊ะที่ว่างอยู่ในตอนนี้\n" + "\t".join(available_tables)
    

@app.route('/reserve_tablecon', methods=['POST'])
def reserve_tablecon():

    # รับค่า table_number และ customer_id จากพารามิเตอร์ใน params ของคำขอ
    table_number = request.args.get('table_number')
    customer_id = request.args.get('customer_id')

    # ตรวจสอบว่าโต๊ะมีอยู่ในฐานข้อมูลหรือไม่
    table = TableNumber.query.filter_by(table_number=table_number).first()
    if not table:
        # ถ้าไม่พบโต๊ะที่ตรงกับ table_number จะส่งข้อความแสดงข้อผิดพลาดกลับไป
        return Response("กรุณาเลือกโต๊ะที่ต้องการใหม่อีกครั้ง", status=400, mimetype='text/plain')

    # ตรวจสอบว่าในวันนั้นมีคอนเสิร์ตหรือไม่
    if not table.con_day:
        # ถ้าในวันนั้นไม่มีคอนเสิร์ต จะส่งข้อความแสดงข้อผิดพลาดกลับไป
        return Response("ตอนนี้ยังไม่มีคอน", status=400, mimetype='text/plain')

    # ตรวจสอบว่าโต๊ะถูกจองแล้วหรือไม่
    if table.tablecon_status == 1:
        # ถ้าโต๊ะถูกจองแล้ว จะส่งข้อความแสดงข้อผิดพลาดกลับไป
        return Response("โต๊ะนี้ถูกจองแล้ว กรุณาเลือกโต๊ะใหม่", status=400, mimetype='text/plain')

    # อัปเดตข้อมูลโต๊ะ
    table.customercon_id = customer_id
    table.tablecon_status = 1

    # บันทึกการเปลี่ยนแปลงลงในฐานข้อมูล
    db.session.commit()

    # ส่งข้อมูลยืนยันการจองกลับไปยังผู้ใช้
    confirmation_message = f"ยืนยันการจอง\nหมายเลขโต๊ะ: {table.table_number}\nมาเอาโต๊ะก่อน 20.30 นะครับ"

    return Response(confirmation_message, status=200, mimetype='text/plain')



# _____________________________________________________________________________________________________________________

# สร้างเลขโต๊ะ
def populate_table_numbers():
    table_names = [
        'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10', 'A11', 'A12', 'A13', 'A14',
        'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8'
    ]

    for table_name in table_names:
       

        existing_table = TableNumber.query.filter_by(table_number=table_name).first()
        if not existing_table:
            table = TableNumber(table_number=table_name)
            db.session.add(table)

    db.session.commit()

# _____________________________________________________________________________________________________________________
# สั่งอาหาร
@app.route('/order', methods=['POST'])
def order_amount():
    # รับค่า customer_id, name_food, และ amount จากพารามิเตอร์ใน URL ของคำขอ
    customer_id = request.args.get('customer_id')
    name_food = request.args.get('name_food')
    amount = request.args.get('amount')

    # ตรวจสอบว่าทุกค่าถูกส่งมาหรือไม่
    if not customer_id or not name_food or not amount:
        return "กรุณากรอกข้อมูลให้ครบถ้วน", 400
    
    # แปลงจำนวนสินค้าเป็นตัวเลข
    try:
        amount = int(amount)
    except ValueError:
        return "จำนวนสินค้าต้องเป็นตัวเลข", 400

    # ตรวจสอบว่าจำนวนสินค้ามากกว่า 0 หรือไม่
    if amount <= 0:
        return "จำนวนสินค้าต้องมากกว่า 0", 400

    # ค้นหา table_number โดยใช้ customer_id
    table_entry = TableNumber.query.filter_by(customer_id=customer_id).first()
    if table_entry is None:
        return "โปรดจองโต๊ะก่อนสั่งอาหาร", 404

    table_number = table_entry.table_number

    # ค้นหาอาหารจาก name_food
    food_entry = Food.query.filter_by(name_food=name_food).first()
    if food_entry is None:
        return "ไม่พบข้อมูลอาหาร", 404

    # แปลงเวลาปัจจุบันเป็นเวลาของไทย
    thai_time = datetime.now(thai_timezone)

    # สร้างใบสั่งซื้อใหม่โดยไม่รวม pay_status
    new_order = Order(
        table_number=table_number,
        id_food=food_entry.id_food,
        name_food=food_entry.name_food,
        price=food_entry.price,
        amount=amount,
        total=food_entry.price * amount,
        order_date=thai_time  # ใช้เวลาของไทย
    )

    # เพิ่มใบสั่งซื้อใหม่ลงในฐานข้อมูล
    db.session.add(new_order)
    db.session.commit()

    # เรียกใช้ฟังก์ชัน send_to_rabbitmq เพื่อส่งข้อมูลไปยัง RabbitMQ
    send_to_rabbitmq(
        new_order.id,
        new_order.table_number,
        new_order.id_food,
        new_order.name_food,
        new_order.price,
        new_order.amount,
        new_order.total,
        new_order.order_date
    )

    # ส่งข้อความยืนยันการรับออเดอร์กลับเป็นข้อความปกติ
    return "ทำการรับออเดอร์เรียบร้อย"



# _____________________________________________________________________________________________________________________

@app.route('/calculate_total', methods=['GET'])
def calculate_total():
    # รับค่า customer_id จากพารามิเตอร์ใน URL ของคำขอ
    customer_id = request.args.get('customer_id')
    if not customer_id:
        return "Customer ID is required", 400

    try:
        # ค้นหาโต๊ะที่มี customer_id ตรงกับที่ได้รับ
        table_number_entry = TableNumber.query.filter_by(customer_id=customer_id).first()
        if not table_number_entry:
            return "Customer ID not found", 404

        table_number = table_number_entry.table_number
        print(f"Table number for customer {customer_id} is {table_number}")

        # ค้นหาใบสั่งซื้อที่มีเลขโต๊ะตรงกับที่ค้นหาและวันที่เป็นวันปัจจุบัน
        # ดึงวันเวลาปัจจุบันในเขตเวลาไทย
        today = datetime.now(thai_timezone).date()
        orders = Order.query.filter(Order.table_number == table_number, db.func.date(Order.order_date) == today).all()
        if not orders:
            return "No orders found for this table today", 404

        print(f"Found {len(orders)} orders for table number {table_number} on {today}")

        # สร้าง dictionary เพื่อเก็บข้อมูลอาหารและจำนวนที่สั่งซื้อ
        order_summary = {}
        Grand_total = 0

        for order in orders:
            if order.id_food not in order_summary:
                order_summary[order.id_food] = {
                    'name_food': order.name_food,
                    'price': order.price,
                    'amount': 0,
                    'totalid': 0
                }
            order_summary[order.id_food]['amount'] += order.amount
            order_summary[order.id_food]['totalid'] += order.price * order.amount
            Grand_total += order.price * order.amount

        # ตรวจสอบค่า order_summary และ Grand_total
        print("Order Summary:", order_summary)
        print("Grand Total:", Grand_total)

        # บันทึก Grand_total ลงในตาราง TableNumber
        table_number_entry.Grand_Total = Grand_total
        db.session.commit()

        # สร้างข้อความรายละเอียดใบเสร็จ
        receipt_lines = [f"นี่คือใบเสร็จของคุณสำหรับโต๊ะหมายเลข {table_number}\n"]
        for item in order_summary.values():
            receipt_lines.append(
                f"{item['name_food']}: ราคา {item['price']} บาท จำนวน {item['amount']} รวม {item['totalid']} บาท"
            )
        receipt_lines.append(f"\nยอดรวมทั้งหมด: {Grand_total} บาท")

        # รวมข้อความทั้งหมดเป็นหนึ่งข้อความ
        receipt_text = "\n".join(receipt_lines)
        print(receipt_text)
        # ส่งผลลัพธ์เป็น plain text
        return receipt_text, 200
    except Exception as e:
        # ส่งข้อความแสดงข้อผิดพลาดหากมีข้อผิดพลาดในการคำนวณหรือบันทึกข้อมูล
        return f'Error calculating total: {str(e)}', 500


# _____________________________________________________________________________________________________________________

# เพิ่มรายการอาหารใหม่
@app.route('/add_food', methods=['POST'])
def add_food():
    name_food = request.args.get('name_food')  # รับค่า name_food จากพารามิเตอร์ใน URL
    price = request.args.get('price')  # รับค่า price จากพารามิเตอร์ใน URL
    
    new_food = Food(name_food=name_food, price=price)  # สร้างอ็อบเจ็กต์ Food ใหม่ด้วยข้อมูลที่ได้รับมา
    db.session.add(new_food)  # เพิ่มข้อมูลอาหารใหม่ลงใน session ของฐานข้อมูล
    db.session.commit()  # บันทึกการเปลี่ยนแปลงลงในฐานข้อมูล
    
    return jsonify({"message": "Food added successfully"})  # ส่งข้อความยืนยันการเพิ่มอาหารกลับไปยังผู้ใช้

# อัพเดทอาหาร
@app.route('/food/<int:id_food>', methods=['PUT'])
def update_food(id_food):
    # รับข้อมูลที่จะใช้ในการอัปเดตจาก URL parameters
    name_food = request.args.get('name_food')
    price = request.args.get('price')

    # ค้นหาข้อมูลอาหารที่ต้องการอัปเดต
    food = Food.query.get(id_food)
    if food is None:
        return jsonify({'error': 'ไม่พบข้อมูลอาหาร'}), 404

    # ตรวจสอบว่าไม่มีการเปลี่ยนแปลง id_food
    if id_food != food.id_food:
        return jsonify({'error': 'ไม่อนุญาตให้เปลี่ยนแปลง id_food'}), 400

    # อัปเดตข้อมูล
    if name_food is not None:
        food.name_food = name_food
    if price is not None:
        food.price = int(price)

    # บันทึกการเปลี่ยนแปลงลงในฐานข้อมูล
    db.session.commit()

    # ส่งข้อความยืนยันการอัปเดตกลับ
    return jsonify({'message': 'อัปเดตข้อมูลอาหารเรียบร้อย'}), 200

# _____________________________________________________________________________________________________________________

# สมัครสมาชิก
@app.route('/update_member_card', methods=['POST'])
def update_member_card():
    customer_id = request.args.get('customer_id')  # รับค่า customer_id จากพารามิเตอร์ใน URL
    user = User.query.get(customer_id)  # ค้นหาผู้ใช้ตาม customer_id
    
    if user:
        user.member_card = 1  # อัปเดตสถานะบัตรสมาชิกเป็น 1
        
        # แปลงเวลาปัจจุบันเป็นเวลาของไทย
        thai_time = datetime.now(thai_timezone)
        user.member_date = thai_time  # บันทึกเวลาที่อัปเดตในรูปแบบของไทย
        
        db.session.commit()  # บันทึกการเปลี่ยนแปลงลงในฐานข้อมูล
        return jsonify({"message": "Member card updated successfully"})  # ส่งข้อความยืนยันการอัปเดตกลับไปยังผู้ใช้
    else:
        return jsonify({"error": "User not found"}), 404  # ส่งข้อความแสดงข้อผิดพลาดกลับไปถ้าไม่พบผู้ใช้

# _____________________________________________________________________________________________________________________

# เพิ่มวันคอน
@app.route('/update_con_day', methods=['POST'])
def update_con_day():
    # รับค่า con_day จากข้อมูลที่ส่งมา
    con_day_str = request.args.get('con_day')

    # แปลงข้อความเป็นวัตถุ datetime
    con_day = datetime.strptime(con_day_str, '%Y-%m-%d')

    # แปลงเวลาเป็นเวลาของไทย
    con_day_thai = con_day.replace(tzinfo=timezone('UTC')).astimezone(thai_timezone)

    # ค้นหาโต๊ะทั้งหมด
    tables = TableNumber.query.all()
    
    # อัปเดตวันที่คอนเสิร์ตของโต๊ะทุกโต๊ะ
    for table in tables:
        table.con_day = con_day_thai
    
    db.session.commit()  # บันทึกการเปลี่ยนแปลงลงในฐานข้อมูล
    return jsonify({"message": "Concert day updated successfully"})  # ส่งข้อความยืนยันการอัปเดตกลับไปยังผู้ใช้
# _____________________________________________________________________________________________________________________

# เรียกพนักงาน
@app.route('/get_table_number', methods=['GET'])
def get_table_number():
    customer_id = request.args.get('customer_id')

    # ตรวจสอบว่ามี customer_id ที่ร้องขอหรือไม่
    if not customer_id:
        return Response('Missing customer_id parameter', status=400, mimetype='text/plain')

    # ค้นหา table_number จาก customer_id ในฐานข้อมูล
    table = TableNumber.query.filter_by(customer_id=customer_id).first()
    
    if table:
        table_number = table.table_number
        message = f'ตอนนี้ได้ทำการเรียกพนักงานให้แล้ว กรุณารอซักครู่ที่ {table_number}'
        
        send_staff(table_number)
        
        return Response(message, status=200, mimetype='text/plain')
    else:
        return Response('Customer not found', status=404, mimetype='text/plain')

# _____________________________________________________________________________________________________________________

    

# เมื่อปิดแอพพลิเคชัน
@app.teardown_appcontext
def shutdown_scheduler_on_teardown(exception=None):
    shutdown_scheduler()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        populate_table_numbers()
    app.run(debug=True)
