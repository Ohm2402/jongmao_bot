from locust import HttpUser, TaskSet, task, between

class UserBehavior(TaskSet):
    
    @task(1)
    def add_user(self):
        self.client.post("/user", params={
            "customer_id": "12345",
            "p_display_name": "Test User",
            "customer_phone": "0812345678"
        })
    
    @task(1)
    def get_user(self):
        self.client.get("/get_user", params={"customer_id": "12345"})
    
    @task(1)
    def ctable(self):
        self.client.get("/Ctable")
    
    @task(1)
    def reserve_table(self):
        self.client.post("/reserve_table", params={
            "table_number": "A1",
            "customer_id": "12345"
        })
    
    @task(1)
    def order_food(self):
        self.client.post("/order", params={
            "customer_id": "12345",
            "name_food": "Test Food",
            "amount": "2"
        })
    
    @task(1)
    def calculate_total(self):
        self.client.get("/calculate_total", params={"customer_id": "12345"})
    
    @task(1)
    def add_food(self):
        self.client.post("/add_food", params={
            "name_food": "Test Food",
            "price": "100"
        })

    @task(1)
    def update_member_card(self):
        self.client.post("/update_member_card", params={"customer_id": "12345"})
    
    @task(1)
    def update_con_day(self):
        self.client.post("/update_con_day", params={"con_day": "2024-12-31"})

    @task(1)
    def get_table_number(self):
        self.client.get("/get_table_number", params={"customer_id": "12345"})
    
    @task(1)
    def verify_slip(self):
        with open("test_slip.jpg", "rb") as file:
            self.client.post("/verify_slip", files={"file": file}, data={"customer_id": "12345"})

class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 3)

    def on_start(self):
        self.user_count = 0

    def on_stop(self):
        self.user_count += 1
        if self.user_count == 1:
            self.stop()

if __name__ == "__main__":
    import os
    os.system("locust")
