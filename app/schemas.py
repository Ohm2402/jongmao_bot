from app import ma
from app.models import User, TableNumber, Food, Order

# สร้าง Schema สำหรับโมเดล User
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User

# สร้าง Schema สำหรับโมเดล TableNumber
class TableNumberSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TableNumber

# สร้าง Schema สำหรับโมเดล Food
class FoodSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Food

# สร้าง Schema สำหรับโมเดล Order
class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order

# สร้าง instance ของ Schema สำหรับแต่ละโมเดล
user_schema = UserSchema()  # Schema สำหรับโมเดล User
users_schema = UserSchema(many=True)  # Schema สำหรับรายการของโมเดล User
table_number_schema = TableNumberSchema()  # Schema สำหรับโมเดล TableNumber
table_numbers_schema = TableNumberSchema(many=True)  # Schema สำหรับรายการของโมเดล TableNumber
food_schema = FoodSchema()  # Schema สำหรับโมเดล Food
foods_schema = FoodSchema(many=True)  # Schema สำหรับรายการของโมเดล Food
order_schema = OrderSchema()  # Schema สำหรับโมเดล Order
orders_schema = OrderSchema(many=True)  # Schema สำหรับรายการของโมเดล Order
