# generate_sample_data

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Generate 10,000 sales transactions
np.random.seed(42)
num_records = 10000

# Date range: last 90 days
end_date = datetime.now()
start_date = end_date - timedelta(days=90)
dates = pd.date_range(start=start_date, end=end_date, periods=num_records)

# Sample data
products = ['Laptop', 'Mouse', 'Keyboard', 'Monitor', 'Webcam', 'Headphones', 'USB Cable', 'Desk Mat']
regions = ['North', 'South', 'East', 'West']
customers = [f'CUST{str(i).zfill(4)}' for i in range(1, 501)]

data = {
    'transaction_id': [f'TXN{str(i).zfill(6)}' for i in range(1, num_records + 1)],
    'date': dates,
    'customer_id': [random.choice(customers) for _ in range(num_records)],
    'product': [random.choice(products) for _ in range(num_records)],
    'quantity': np.random.randint(1, 10, num_records),
    'unit_price': np.random.uniform(10, 500, num_records).round(2),
    'region': [random.choice(regions) for _ in range(num_records)]
}

df = pd.DataFrame(data)
df['total_amount'] = (df['quantity'] * df['unit_price']).round(2)

# Save as CSV
df.to_csv('sales_data.csv', index=False)
print(f"✅ Generated {len(df)} sales records")
print(df.head())




