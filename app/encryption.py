from cryptography.fernet import Fernet
import os

# ฟังก์ชันสำหรับโหลดคีย์จากไฟล์
def load_key(file_path='secret.key'):
    return open(file_path, 'rb').read()

# ตรวจสอบว่ามีไฟล์ secret.key อยู่หรือไม่ ถ้าไม่มีให้แจ้งเตือน
if not os.path.exists('secret.key'):
    print("ไม่พบไฟล์ secret.key กรุณาสร้างคีย์ใหม่")
    exit()

# โหลดคีย์จากไฟล์
key = load_key()

def encrypt_data(data, key):
    cipher_suite = Fernet(key)
    encrypted_data = cipher_suite.encrypt(data.encode()).decode()
    return encrypted_data

def decrypt_data(encrypted_data, key):
    cipher_suite = Fernet(key)
    decrypted_data = cipher_suite.decrypt(encrypted_data.encode()).decode()
    return decrypted_data

