# run.py: ไฟล์นี้ใช้สำหรับเรียกใช้แอปพลิเคชัน เริ่มต้นเซิร์ฟเวอร์และรันแอปพลิเคชัน
from app import app, db


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True, port=9939)