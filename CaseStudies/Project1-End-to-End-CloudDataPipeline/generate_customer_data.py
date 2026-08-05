import json
import random
from datetime import datetime, timedelta

# Generate customer demographics for 500 customers
customers = [f'CUST{str(i).zfill(4)}' for i in range(1, 501)]
age_groups = ['18-25', '26-35', '36-45', '46-55', '56+']
membership_tiers = ['Bronze', 'Silver', 'Gold', 'Platinum']

customer_data = []
for customer in customers:
    # Generate random signup date within last 2 years
    days_ago = random.randint(1, 730)
    signup_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    
    customer_data.append({
        'customer_id': customer,
        'age_group': random.choice(age_groups),
        'membership_tier': random.choice(membership_tiers),
        'signup_date': signup_date
    })

# Save as JSON
with open('customer_demographics.json', 'w') as f:
    for record in customer_data:
        f.write(json.dumps(record) + '\n')

print(f"✅ Generated {len(customer_data)} customer records")
print("Sample records:")
for record in customer_data[:3]:
    print(record)



