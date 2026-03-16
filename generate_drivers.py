import json
import random

regions = ["TN", "AP", "KA", "MH", "DL", "TS", "UP"]
first_names = ["Ravi", "Ajay", "Kiran", "Amit", "Rahul", "Priya", "Sneha", "Vikram", "Suresh", "Ramesh", "Gita", "Sita", "Arjun", "Karthik", "Deepa", "Pooja", "Meera", "Vijay", "Sanjay", "Rajesh", "Anil", "Sunil", "Prakash", "Anita", "Sunita", "Manoj", "Anand", "Ashok", "Kavita", "Geeta"]
last_names = ["Kumar", "Sharma", "Singh", "Reddy", "Patel", "Rao", "Nair", "Iyer", "Yadav", "Gupta", "Jain", "Bose", "Das", "Menon", "Pillai", "Verma", "Mishra", "Pandey"]

drivers = {}

# Ensure the exact user-requested data is present
drivers["TN10AB1234"] = {"name": "Ravi Kumar", "phone": "9876543210", "email": "ravi@gmail.com"}
drivers["AP39CD5678"] = {"name": "Pream", "phone": "+919014390204", "email": "pream4227@gmail.com"}
drivers["KA05EF1111"] = {"name": "Kiran", "phone": "9111111111", "email": "kiran@gmail.com"}

while len(drivers) < 100:
    region = random.choice(regions)
    district = f"{random.randint(1, 99):02d}"
    alpha = chr(random.randint(65, 90)) + chr(random.randint(65, 90))
    number = f"{random.randint(1000, 9999)}"
    plate = f"{region}{district}{alpha}{number}"
    
    if plate not in drivers:
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        phone = f"9{random.randint(100000000, 999999999)}"
        email = f"{name.split()[0].lower()}{random.randint(1,999)}@gmail.com"
        drivers[plate] = {"name": name, "phone": phone, "email": email}

with open('drivers.json', 'w') as f:
    json.dump(drivers, f, indent=4)

print("drivers.json generated with 100 records successfully!")
