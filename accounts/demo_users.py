"""Development-only demonstration accounts (documented in README.md).

These credentials are intentionally public and weak. They are created ONLY by
`manage.py seed_demo_data --with-demo-users` and ONLY when
settings.ALLOW_DEMO_ACCOUNTS is True (defaults to DEBUG).
"""

DEMO_CUSTOMERS = [
    # username, password, first name, last name, email, phone, city, state
    ("niraj_dalal", "1234", "Niraj", "Dalal", "niraj.dalal@example.com", "9810000001", "New Delhi", "Delhi"),
    ("novamart_customer01", "NovaDemo@01!", "Aarav", "Mehta", "customer01@example.com", "9810000002", "Mumbai", "Maharashtra"),
    ("novamart_customer02", "NovaDemo@02!", "Diya", "Sharma", "customer02@example.com", "9810000003", "Jaipur", "Rajasthan"),
    ("novamart_customer03", "NovaDemo@03!", "Kabir", "Singh", "customer03@example.com", "9810000004", "Chandigarh", "Chandigarh"),
    ("novamart_customer04", "NovaDemo@04!", "Isha", "Nair", "customer04@example.com", "9810000005", "Kochi", "Kerala"),
    ("novamart_customer05", "NovaDemo@05!", "Rohan", "Iyer", "customer05@example.com", "9810000006", "Chennai", "Tamil Nadu"),
    ("novamart_customer06", "NovaDemo@06!", "Meera", "Patel", "customer06@example.com", "9810000007", "Ahmedabad", "Gujarat"),
    ("novamart_customer07", "NovaDemo@07!", "Vihaan", "Rao", "customer07@example.com", "9810000008", "Bengaluru", "Karnataka"),
    ("novamart_customer08", "NovaDemo@08!", "Anaya", "Gupta", "customer08@example.com", "9810000009", "Lucknow", "Uttar Pradesh"),
    ("novamart_customer09", "NovaDemo@09!", "Arjun", "Das", "customer09@example.com", "9810000010", "Kolkata", "West Bengal"),
]

DEMO_ADMIN = ("novamart_admin", "NovaAdmin@2026!", "Nova", "Admin", "admin@example.com")
