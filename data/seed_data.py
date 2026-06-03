"""Run directly: python data/seed_data.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import random
from datetime import datetime, timedelta
from faker import Faker
from src.db.sql_db import init_db, get_session, Customer, SupportTicket, Product, Order

fake = Faker()
random.seed(42)
Faker.seed(42)

ACCOUNT_TYPES = ["standard", "premium", "enterprise"]
CATEGORIES = ["billing", "technical", "shipping", "returns", "general"]
STATUSES = ["open", "in_progress", "resolved", "closed"]
PRIORITIES = ["low", "medium", "high", "critical"]
ORDER_STATUSES = ["delivered", "shipped", "processing", "cancelled", "refunded"]

PRODUCTS_DATA = [
    ("Laptop Pro 15", "Electronics", 1299.99, "High-performance 15-inch laptop with M3 chip"),
    ("Wireless Mouse", "Accessories", 29.99, "Ergonomic wireless mouse with long battery life"),
    ("USB-C Hub 7-in-1", "Accessories", 49.99, "7-port USB-C hub with HDMI, SD card, and USB-A"),
    ("Monitor 27\" 4K", "Electronics", 399.99, "27-inch 4K IPS monitor with HDR support"),
    ("Mechanical Keyboard", "Accessories", 149.99, "Tenkeyless RGB mechanical keyboard"),
    ("Webcam HD 1080p", "Electronics", 79.99, "1080p webcam with built-in noise-cancelling mic"),
    ("External SSD 1TB", "Storage", 129.99, "Portable NVMe SSD, read speeds up to 1050MB/s"),
    ("Noise-Cancelling Headphones", "Audio", 249.99, "ANC headphones with 30-hour battery life"),
    ("Phone Stand Adjustable", "Accessories", 19.99, "Aluminium adjustable phone/tablet stand"),
    ("Software License Annual", "Software", 99.99, "Annual subscription for productivity suite"),
]

TICKET_TEMPLATES = {
    "billing": [
        "Invoice discrepancy on recent order",
        "Double charge on my account",
        "Incorrect tax calculation on invoice",
        "Subscription renewal charge issue",
        "Request for detailed billing statement",
    ],
    "technical": [
        "Product not powering on after delivery",
        "Software compatibility issue with macOS",
        "Device performance degradation after update",
        "Cannot connect to Bluetooth accessories",
        "Error code appearing on device startup",
    ],
    "shipping": [
        "Package not delivered — tracking shows delivered",
        "Wrong item received in shipment",
        "Product arrived damaged",
        "Tracking number not updating for 5 days",
        "Need to update delivery address",
    ],
    "returns": [
        "Return request for defective product",
        "Refund not received after return was accepted",
        "Exchange request for wrong size/color",
        "Return label not received via email",
        "Partial return request for bundle order",
    ],
    "general": [
        "Inquiry about product compatibility",
        "Account upgrade to premium tier",
        "Loyalty points balance discrepancy",
        "Bulk order discount inquiry",
        "General product feature questions",
    ],
}


def _rand_date(days_ago_max: int = 365) -> str:
    return (datetime.now() - timedelta(days=random.randint(0, days_ago_max))).strftime("%Y-%m-%d")


def seed():
    init_db()
    session = get_session()

    # Clear tables in dependency order
    session.query(Order).delete()
    session.query(SupportTicket).delete()
    session.query(Customer).delete()
    session.query(Product).delete()
    session.commit()

    # ── Products ──────────────────────────────────────────────────────────────
    products = []
    for name, cat, price, desc in PRODUCTS_DATA:
        p = Product(name=name, category=cat, price=price, description=desc)
        session.add(p)
        products.append(p)
    session.commit()

    # ── Customers (25 synthetic + 1 named test customer) ─────────────────────
    customers = []
    emails_used: set[str] = set()

    for _ in range(25):
        email = fake.unique.email()
        while email in emails_used:
            email = fake.unique.email()
        emails_used.add(email)
        c = Customer(
            name=fake.name(),
            email=email,
            phone=fake.phone_number()[:15],
            account_type=random.choice(ACCOUNT_TYPES),
            location=f"{fake.city()}, {fake.state_abbr()}",
            join_date=_rand_date(730),
            loyalty_points=random.randint(0, 5000),
        )
        session.add(c)
        customers.append(c)

    # Known test customer referenced in the assignment brief
    ema = Customer(
        name="Ema Johnson",
        email="ema.johnson@example.com",
        phone="555-0123",
        account_type="premium",
        location="New York, NY",
        join_date="2023-01-15",
        loyalty_points=2450,
    )
    session.add(ema)
    session.commit()
    customers.append(ema)

    # ── Support Tickets ───────────────────────────────────────────────────────
    for customer in customers:
        for _ in range(random.randint(2, 5)):
            category = random.choice(CATEGORIES)
            subject = random.choice(TICKET_TEMPLATES[category])
            created = _rand_date(180)
            status = random.choice(STATUSES)
            resolved = None
            if status in ("resolved", "closed"):
                resolved = (
                    datetime.strptime(created, "%Y-%m-%d") + timedelta(days=random.randint(1, 14))
                ).strftime("%Y-%m-%d")

            t = SupportTicket(
                customer_id=customer.id,
                subject=subject,
                description=fake.paragraph(nb_sentences=3),
                category=category,
                status=status,
                priority=random.choice(PRIORITIES),
                created_at=created,
                updated_at=created,
                resolved_at=resolved,
                agent_notes=fake.sentence() if status in ("resolved", "closed") else None,
            )
            session.add(t)

        # Orders (1-3 per customer)
        for _ in range(random.randint(1, 3)):
            product = random.choice(products)
            qty = random.randint(1, 3)
            session.add(Order(
                customer_id=customer.id,
                product_id=product.id,
                quantity=qty,
                total_amount=round(product.price * qty, 2),
                order_date=_rand_date(365),
                status=random.choice(ORDER_STATUSES),
            ))

    # Specific rich history for Ema
    ema_tickets = [
        SupportTicket(
            customer_id=ema.id,
            subject="Refund request for damaged Laptop Pro 15",
            description="My laptop arrived with a cracked screen. I have photos of the damage. Requesting full refund.",
            category="returns",
            status="in_progress",
            priority="high",
            created_at="2024-03-10",
            updated_at="2024-03-11",
        ),
        SupportTicket(
            customer_id=ema.id,
            subject="Software license activation key not working",
            description="The license key in my confirmation email shows as 'already used'. Unable to activate on my MacBook.",
            category="technical",
            status="resolved",
            priority="high",
            created_at="2024-02-05",
            updated_at="2024-02-07",
            resolved_at="2024-02-07",
            agent_notes="Sent replacement key via email. Customer confirmed activation successful.",
        ),
        SupportTicket(
            customer_id=ema.id,
            subject="Double charge — March subscription renewal",
            description="My credit card was charged twice ($99.99 x2) for the March annual renewal. Please refund the duplicate.",
            category="billing",
            status="resolved",
            priority="critical",
            created_at="2024-03-01",
            updated_at="2024-03-02",
            resolved_at="2024-03-02",
            agent_notes="Duplicate charge confirmed. Refund of $99.99 processed. Reference: REF-2024-0302.",
        ),
        SupportTicket(
            customer_id=ema.id,
            subject="Webcam not detected on Windows 11",
            description="Webcam HD 1080p is not detected by Windows 11. Device Manager shows 'Unknown Device'.",
            category="technical",
            status="open",
            priority="medium",
            created_at="2024-03-20",
            updated_at="2024-03-20",
        ),
    ]
    for t in ema_tickets:
        session.add(t)

    session.commit()
    session.close()

    total_tickets = sum(3 for _ in range(25)) + len(ema_tickets)
    print(f"✓ {len(products)} products seeded")
    print(f"✓ {len(customers)} customers seeded (incl. Ema Johnson)")
    print(f"✓ Support tickets and orders seeded")
    print("  Ready. Run: streamlit run app/main.py")


if __name__ == "__main__":
    seed()
