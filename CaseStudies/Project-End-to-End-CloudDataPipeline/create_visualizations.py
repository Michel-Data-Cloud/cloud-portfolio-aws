"""
Data Visualization Script - AWS Data Pipeline Project
Purpose: Generate professional charts from Athena query results
Author: Jack
Date: December 2025

This script:
1. Connects to AWS Athena using boto3
2. Runs analytical SQL queries on processed sales data
3. Generates 6 professional visualizations
4. Saves charts as PNG files for portfolio documentation
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pyathena import connect
import os

# Set visualization style for professional appearance
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

# Create screenshots folder if it doesn't exist
# This is where all generated charts will be saved
if not os.path.exists('screenshots'):
    os.makedirs('screenshots')
    print("✅ Created 'screenshots' folder")

print("========== Connecting to AWS Athena ==========")

# Connect to Athena using AWS credentials from your ~/.aws/credentials
# No need to provide access keys here - boto3 uses your configured AWS CLI credentials
# Database: Your Athena database created in Day 4
# S3 staging: Where Athena stores query results temporarily
# Region: Must match where your data lives (us-east-1)
try:
    conn = connect(
        s3_staging_dir='s3://michel-athena-results-project1-dec2025/',  # Your Athena results bucket
        region_name='us-east-1',                               # Your AWS region
        database='project1_sales_analytics_db'                          # Your Athena database name (or project1_sales_analytics_db if you used that)
    )
    print("✅ Connected to Athena successfully!")
except Exception as e:
    print(f"❌ Failed to connect to Athena: {e}")
    print("Make sure:")
    print("  1. AWS CLI is configured (aws configure)")
    print("  2. Your credentials have Athena permissions")
    print("  3. Database name matches what you created in Day 4")
    exit(1)

# ============================================
# CHART 1: SALES BY REGION (BAR CHART)
# ============================================
print("\n========== Creating Chart 1: Sales by Region ==========")

# Query Athena for revenue by region
# This runs the SQL query directly on your Athena data warehouse
query1 = """
SELECT 
    region,
    SUM(total_amount) as total_revenue,
    COUNT(*) as transaction_count
FROM project1_sales_analytics_db.enriched_sales
GROUP BY region
ORDER BY total_revenue DESC
"""

try:
    df_region = pd.read_sql(query1, conn)
    print(f"✅ Retrieved {len(df_region)} regions")
    
    # Create figure and axis for plotting
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create bar chart
    # x-axis: regions, y-axis: revenue
    # Color palette: professional blue gradient
    bars = ax.bar(df_region['region'], df_region['total_revenue'], 
                   color=sns.color_palette("Blues_r", len(df_region)))
    
    # Add value labels on top of each bar
    # Shows exact revenue amount for easy reading
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'${height:,.0f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Chart formatting
    ax.set_title('Total Revenue by Region', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Region', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Revenue ($)', fontsize=12, fontweight='bold')
    
    # Format y-axis to show currency with commas
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # Add grid for easier reading
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('screenshots/01_revenue_by_region.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved: screenshots/01_revenue_by_region.png")
    
except Exception as e:
    print(f"❌ Error creating Chart 1: {e}")

# ============================================
# CHART 2: TOP PRODUCTS BY REVENUE (HORIZONTAL BAR)
# ============================================
print("\n========== Creating Chart 2: Top Products ==========")

query2 = """
SELECT 
    product,
    SUM(total_amount) as total_revenue,
    COUNT(*) as units_sold
FROM project1_sales_analytics_db.enriched_sales
GROUP BY product
ORDER BY total_revenue DESC
"""

try:
    df_products = pd.read_sql(query2, conn)
    print(f"✅ Retrieved {len(df_products)} products")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Horizontal bar chart (easier to read product names)
    bars = ax.barh(df_products['product'], df_products['total_revenue'],
                    color=sns.color_palette("viridis", len(df_products)))
    
    # Add value labels at end of each bar
    for bar in bars:
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2.,
                f'${width:,.0f}',
                ha='left', va='center', fontsize=9, fontweight='bold')
    
    ax.set_title('Top Products by Revenue', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Total Revenue ($)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Product', fontsize=12, fontweight='bold')
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('screenshots/02_top_products.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved: screenshots/02_top_products.png")
    
except Exception as e:
    print(f"❌ Error creating Chart 2: {e}")

# ============================================
# CHART 3: MONTHLY REVENUE TREND (LINE CHART)
# ============================================
print("\n========== Creating Chart 3: Monthly Trend ==========")

query3 = """
SELECT 
    year,
    month,
    SUM(total_amount) as total_revenue,
    COUNT(*) as transaction_count
FROM project1_sales_analytics_db.enriched_sales
GROUP BY year, month
ORDER BY year, month
"""

try:
    df_monthly = pd.read_sql(query3, conn)
    print(f"✅ Retrieved {len(df_monthly)} months of data")
    
    # Create month labels (e.g., "2025-09", "2025-10")
    df_monthly['month_label'] = df_monthly['year'].astype(str) + '-' + df_monthly['month'].astype(str).str.zfill(2)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Line chart with markers
    ax.plot(df_monthly['month_label'], df_monthly['total_revenue'], 
            marker='o', linewidth=2.5, markersize=8, color='#2E86AB')
    
    # Add value labels on each point
    for i, row in df_monthly.iterrows():
        ax.text(i, row['total_revenue'], f"${row['total_revenue']:,.0f}",
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax.set_title('Monthly Revenue Trend', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Month', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Revenue ($)', fontsize=12, fontweight='bold')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('screenshots/03_monthly_trend.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved: screenshots/03_monthly_trend.png")
    
except Exception as e:
    print(f"❌ Error creating Chart 3: {e}")

# ============================================
# CHART 4: REVENUE BY CUSTOMER TIER (PIE CHART)
# ============================================
print("\n========== Creating Chart 4: Customer Tiers ==========")

query4 = """
SELECT 
    membership_tier,
    SUM(total_amount) as total_revenue,
    COUNT(DISTINCT customer_id) as customer_count
FROM project1_sales_analytics_db.enriched_sales
GROUP BY membership_tier
ORDER BY total_revenue DESC
"""

try:
    df_tiers = pd.read_sql(query4, conn)
    print(f"✅ Retrieved {len(df_tiers)} membership tiers")
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Color scheme for tiers (matches typical tier colors)
    colors = {'Platinum': '#E5E4E2', 'Gold': '#FFD700', 
              'Silver': '#C0C0C0', 'Bronze': '#CD7F32'}
    tier_colors = [colors.get(tier, '#808080') for tier in df_tiers['membership_tier']]
    
    # Create pie chart
    wedges, texts, autotexts = ax.pie(
        df_tiers['total_revenue'],
        labels=df_tiers['membership_tier'],
        autopct='%1.1f%%',
        startangle=90,
        colors=tier_colors,
        textprops={'fontsize': 11, 'fontweight': 'bold'}
    )
    
    # Make percentage text more readable
    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontsize(12)
    
    ax.set_title('Revenue Distribution by Membership Tier', 
                 fontsize=16, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig('screenshots/04_customer_tiers.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved: screenshots/04_customer_tiers.png")
    
except Exception as e:
    print(f"❌ Error creating Chart 4: {e}")

# ============================================
# CHART 5: SPENDING BY AGE GROUP (BAR CHART)
# ============================================
print("\n========== Creating Chart 5: Age Group Analysis ==========")

query5 = """
SELECT 
    age_group,
    SUM(total_amount) as total_revenue,
    COUNT(DISTINCT customer_id) as customer_count,
    AVG(total_amount) as avg_order_value
FROM project1_sales_analytics_db.enriched_sales
GROUP BY age_group
ORDER BY total_revenue DESC
"""

try:
    df_age = pd.read_sql(query5, conn)
    print(f"✅ Retrieved {len(df_age)} age groups")
    
    # Create figure with two subplots side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Left chart: Total revenue by age group
    bars1 = ax1.bar(df_age['age_group'], df_age['total_revenue'],
                     color=sns.color_palette("Oranges_r", len(df_age)))
    
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                 f'${height:,.0f}',
                 ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax1.set_title('Total Revenue by Age Group', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Age Group', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Total Revenue ($)', fontsize=11, fontweight='bold')
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    ax1.grid(axis='y', alpha=0.3)
    
    # Right chart: Average order value by age group
    bars2 = ax2.bar(df_age['age_group'], df_age['avg_order_value'],
                     color=sns.color_palette("Greens_r", len(df_age)))
    
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                 f'${height:.0f}',
                 ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax2.set_title('Average Order Value by Age Group', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Age Group', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Avg Order Value ($)', fontsize=11, fontweight='bold')
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:.0f}'))
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('screenshots/05_age_group_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved: screenshots/05_age_group_analysis.png")
    
except Exception as e:
    print(f"❌ Error creating Chart 5: {e}")

# ============================================
# CHART 6: TRANSACTION DISTRIBUTION (HISTOGRAM)
# ============================================
print("\n========== Creating Chart 6: Transaction Distribution ==========")

query6 = """
SELECT total_amount
FROM project1_sales_analytics_db.enriched_sales
WHERE total_amount > 0
"""

try:
    df_amounts = pd.read_sql(query6, conn)
    print(f"✅ Retrieved {len(df_amounts)} transactions")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Create histogram showing distribution of transaction amounts
    # 50 bins to show the distribution pattern
    n, bins, patches = ax.hist(df_amounts['total_amount'], bins=50, 
                                 color='#A23B72', edgecolor='black', alpha=0.7)
    
    # Color gradient for bins (darker = higher frequency)
    cm = plt.cm.plasma
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    col = bin_centers - min(bin_centers)
    col /= max(col)
    for c, p in zip(col, patches):
        plt.setp(p, 'facecolor', cm(c))
    
    ax.set_title('Distribution of Transaction Amounts', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Transaction Amount ($)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Frequency (Number of Transactions)', fontsize=12, fontweight='bold')
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    ax.grid(axis='y', alpha=0.3)
    
    # Add statistics as text box
    stats_text = f"Mean: ${df_amounts['total_amount'].mean():,.2f}\n"
    stats_text += f"Median: ${df_amounts['total_amount'].median():,.2f}\n"
    stats_text += f"Std Dev: ${df_amounts['total_amount'].std():,.2f}"
    
    ax.text(0.95, 0.95, stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig('screenshots/06_transaction_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved: screenshots/06_transaction_distribution.png")
    
except Exception as e:
    print(f"❌ Error creating Chart 6: {e}")

# Close Athena connection
conn.close()

print("\n" + "="*60)
print("========== ALL VISUALIZATIONS COMPLETE! ==========")
print("="*60)
print("\n📊 Generated 6 professional charts:")
print("  1. ✅ Revenue by Region (Bar Chart)")
print("  2. ✅ Top Products (Horizontal Bar Chart)")
print("  3. ✅ Monthly Revenue Trend (Line Chart)")
print("  4. ✅ Customer Tiers (Pie Chart)")
print("  5. ✅ Age Group Analysis (Dual Bar Charts)")
print("  6. ✅ Transaction Distribution (Histogram)")
print("\n📁 All charts saved in: screenshots/")
print("\n🎯 Next steps:")
print("  1. Review the generated charts")
print("  2. Add them to your GitHub README")
print("  3. Update project documentation")
print("\n✅ Python visualization complete!")






