"""
Synthetic e-commerce dataset generator.

Generates a realistic (but fully synthetic) retail transaction dataset with:
  - channel-correlated customer quality (so CAC/LTV analysis has a real story)
  - seasonality (Nov/Dec holiday lift)
  - a skewed value distribution (so RFM segmentation produces a genuine Pareto pattern)
  - natural churn (customers who stop purchasing)

Deterministic via a fixed random seed -> anyone cloning this repo gets identical data.
"""
import random
import csv
from datetime import date, timedelta
import numpy as np
from faker import Faker

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

START = date(2023, 1, 1)
END = date(2024, 12, 31)

N_CUSTOMERS = 5000
N_PRODUCTS = 150

CHANNELS = ["organic", "paid_search", "social", "email", "referral"]
CHANNEL_WEIGHTS = [0.30, 0.25, 0.20, 0.15, 0.10]
# Multiplier applied to a customer's latent value score, by acquisition channel.
# Referral/organic customers convert better in practice (existing trust); paid
# social/search bring more volume but lower average quality. This is the
# mechanism that produces a genuine CAC/LTV story in the analysis later.
CHANNEL_VALUE_MULT = {"organic": 1.20, "paid_search": 0.80, "social": 0.90, "email": 1.00, "referral": 1.45}
# Target cost-per-acquisition by channel (used to size the marketing_spend table)
CHANNEL_CPA = {"organic": 5, "paid_search": 40, "social": 25, "email": 12, "referral": 8}

REGIONS = ["North", "South", "East", "West", "Central"]

CATEGORIES = {
    "Electronics": (40, 900),
    "Apparel": (12, 150),
    "Home & Kitchen": (15, 300),
    "Beauty": (8, 90),
    "Sports & Outdoors": (10, 250),
    "Books": (6, 45),
    "Toys": (8, 120),
    "Grocery": (3, 60),
}

PAYMENT_METHODS = ["credit_card", "debit_card", "upi", "net_banking", "wallet"]


def month_iter(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield date(y, m, 1)
        m += 1
        if m > 12:
            m = 1
            y += 1


def seasonal_factor(d: date) -> float:
    if d.month in (11, 12):
        return 1.55
    if d.month == 1:
        return 0.80
    if d.month in (6, 7):
        return 1.10
    return 1.00


def random_day_in_month(month_start: date, not_before: date, not_after: date) -> date:
    if month_start.month == 12:
        next_month = date(month_start.year + 1, 1, 1)
    else:
        next_month = date(month_start.year, month_start.month + 1, 1)
    lo = max(month_start, not_before)
    hi = min(next_month - timedelta(days=1), not_after)
    if hi < lo:
        return lo
    span = (hi - lo).days
    return lo + timedelta(days=random.randint(0, span))


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
customers = []
for cid in range(1, N_CUSTOMERS + 1):
    channel = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]
    signup = START + timedelta(days=random.randint(0, (END - START).days))
    value_score = float(np.random.lognormal(mean=0.0, sigma=0.85)) * CHANNEL_VALUE_MULT[channel]
    customers.append({
        "customer_id": cid,
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "signup_date": signup.isoformat(),
        "region": random.choice(REGIONS),
        "acquisition_channel": channel,
        "_value_score": value_score,  # latent, not exported to CSV
    })

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
products = []
pid = 1
cat_names = list(CATEGORIES.keys())
for pid in range(1, N_PRODUCTS + 1):
    cat = random.choice(cat_names)
    lo, hi = CATEGORIES[cat]
    price = round(float(np.random.uniform(lo, hi)), 2)
    cost = round(price * random.uniform(0.45, 0.70), 2)
    products.append({
        "product_id": pid,
        "product_name": f"{cat.split()[0]} {fake.word().capitalize()} {pid}",
        "category": cat,
        "unit_price": price,
        "unit_cost": cost,
    })

# ---------------------------------------------------------------------------
# Orders + order_items (driven by each customer's latent value score)
# ---------------------------------------------------------------------------
orders = []
order_items = []
order_id = 1
order_item_id = 1
channel_new_customers_by_month = {}  # (channel, "YYYY-MM") -> count

for c in customers:
    signup_d = date.fromisoformat(c["signup_date"])
    key = (c["acquisition_channel"], signup_d.strftime("%Y-%m"))
    channel_new_customers_by_month[key] = channel_new_customers_by_month.get(key, 0) + 1

    base_prob = min(max(c["_value_score"] * 0.16, 0.02), 0.85)

    for m_start in month_iter(signup_d.replace(day=1), END):
        if m_start < signup_d.replace(day=1):
            continue
        p = base_prob * seasonal_factor(m_start)
        p = min(p, 0.95)
        if random.random() > p:
            continue  # no purchase this month

        n_orders_this_month = 1 + np.random.poisson(max(c["_value_score"] * 0.25, 0.05))
        n_orders_this_month = int(min(n_orders_this_month, 3))

        for _ in range(n_orders_this_month):
            o_date = random_day_in_month(m_start, signup_d, END)
            status = random.choices(
                ["completed", "cancelled", "returned"], weights=[0.92, 0.05, 0.03], k=1
            )[0]
            orders.append({
                "order_id": order_id,
                "customer_id": c["customer_id"],
                "order_date": o_date.isoformat(),
                "order_status": status,
                "payment_method": random.choice(PAYMENT_METHODS),
            })

            n_items = random.randint(1, 5)
            chosen = random.sample(products, k=n_items)
            for prod in chosen:
                qty = random.randint(1, 3)
                discount = random.choices([0.0, 0.05, 0.10, 0.15, 0.20], weights=[0.6, 0.15, 0.12, 0.08, 0.05], k=1)[0]
                order_items.append({
                    "order_item_id": order_item_id,
                    "order_id": order_id,
                    "product_id": prod["product_id"],
                    "quantity": qty,
                    "unit_price": prod["unit_price"],
                    "discount_pct": discount,
                })
                order_item_id += 1

            order_id += 1

# ---------------------------------------------------------------------------
# Marketing spend (sized so realized CAC ~ target CPA per channel, with noise)
# ---------------------------------------------------------------------------
marketing_spend = []
spend_id = 1
for (channel, ym), n_new in sorted(channel_new_customers_by_month.items(), key=lambda x: (x[0][1], x[0][0])):
    target_cpa = CHANNEL_CPA[channel]
    noise = np.random.uniform(0.85, 1.15)
    spend = round(n_new * target_cpa * noise, 2)
    marketing_spend.append({
        "spend_id": spend_id,
        "channel": channel,
        "month": f"{ym}-01",
        "spend_amount": spend,
    })
    spend_id += 1

# ---------------------------------------------------------------------------
# Write CSVs (drop the latent _value_score before export)
# ---------------------------------------------------------------------------
def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r[k] for k in fieldnames})

write_csv("data/raw/customers.csv", customers,
          ["customer_id", "first_name", "last_name", "email", "signup_date", "region", "acquisition_channel"])
write_csv("data/raw/products.csv", products,
          ["product_id", "product_name", "category", "unit_price", "unit_cost"])
write_csv("data/raw/orders.csv", orders,
          ["order_id", "customer_id", "order_date", "order_status", "payment_method"])
write_csv("data/raw/order_items.csv", order_items,
          ["order_item_id", "order_id", "product_id", "quantity", "unit_price", "discount_pct"])
write_csv("data/raw/marketing_spend.csv", marketing_spend,
          ["spend_id", "channel", "month", "spend_amount"])

print(f"customers:        {len(customers):,}")
print(f"products:         {len(products):,}")
print(f"orders:           {len(orders):,}")
print(f"order_items:      {len(order_items):,}")
print(f"marketing_spend:  {len(marketing_spend):,} rows")
