-- ============================================
-- ATHENA SQL QUERIES - DATA WAREHOUSE ANALYSIS
-- Project: End-to-End AWS Data Pipeline
-- Author: Michel Hidalgo 
-- Date: December 2025
-- ============================================

-- This file contains SQL queries for analyzing processed sales data in AWS Athena
-- Tables: enriched_sales (detailed transactions) and sales_summary (aggregated metrics)

-- ============================================
-- DATA TYPE NOTES
-- ============================================
-- Date Column: Stored as STRING containing timestamp with nanoseconds
--              Format: "2025-10-15 01:45:02.183151148"
-- Date Filtering: Use substring(date, 1, 10) to extract YYYY-MM-DD
--                 More efficient than casting to DATE or TIMESTAMP
-- Example: WHERE substring(date, 1, 10) = '2025-10-15'

-- ============================================
-- SETUP: CREATE DATABASE
-- ============================================

CREATE DATABASE IF NOT EXISTS sales_analytics_db
COMMENT 'Database for querying processed sales data'
LOCATION 's3://michel-processed-data-pipeline-project1/';


-- ============================================
-- SETUP: CREATE ENRICHED SALES TABLE
-- ============================================

CREATE EXTERNAL TABLE IF NOT EXISTS enriched_sales (
    transaction_id STRING,
    date STRING,
    customer_id STRING,
    product STRING,
    quantity INT,
    unit_price DOUBLE,
    region STRING,
    total_amount DOUBLE,
    age_group STRING,
    membership_tier STRING,
    signup_date STRING,
    day INT
)
PARTITIONED BY (
    year INT,
    month INT
)
STORED AS PARQUET
LOCATION 's3://michel-processed-data-pipeline-project1/enriched/'
TBLPROPERTIES (
    'projection.enabled' = 'true',
    'projection.year.type' = 'integer',
    'projection.year.range' = '2024,2026',
    'projection.month.type' = 'integer',
    'projection.month.range' = '1,12',
    'storage.location.template' = 's3://michel-processed-data-pipeline-project1/enriched/year=${year}/month=${month}'
);


-- ============================================
-- SETUP: CREATE SUMMARY TABLE
-- ============================================

CREATE EXTERNAL TABLE IF NOT EXISTS sales_summary (
    region STRING,
    product STRING,
    year INT,
    month INT,
    total_revenue DOUBLE,
    transaction_count BIGINT,
    avg_transaction_value DOUBLE
)
STORED AS PARQUET
LOCATION 's3://michel-processed-data-pipeline-project1/summary/'
TBLPROPERTIES ('parquet.compress'='SNAPPY');


-- ============================================
-- QUERY 1: RECORD COUNT VERIFICATION
-- ============================================
-- Purpose: Verify data was loaded correctly
-- Expected: ~10,000 records

SELECT COUNT(*) as total_records
FROM enriched_sales;


-- ============================================
-- QUERY 2: SAMPLE DATA INSPECTION
-- ============================================
-- Purpose: View sample records to verify data quality
-- Shows: Transaction details with customer demographics

SELECT 
    transaction_id,
    date,
    customer_id,
    product,
    quantity,
    unit_price,
    total_amount,
    region,
    age_group,
    membership_tier
FROM enriched_sales
LIMIT 10;


-- ============================================
-- QUERY 3: SALES PERFORMANCE BY REGION
-- ============================================
-- Purpose: Identify highest-performing regions
-- Business use: Regional sales strategy, resource allocation

SELECT 
    region,
    COUNT(*) as transaction_count,
    SUM(total_amount) as total_revenue,
    ROUND(AVG(total_amount), 2) as avg_order_value
FROM enriched_sales
GROUP BY region
ORDER BY total_revenue DESC;


-- ============================================
-- QUERY 4: TOP PRODUCTS BY REVENUE
-- ============================================
-- Purpose: Identify best-selling products
-- Business use: Inventory planning, marketing focus

SELECT 
    product,
    COUNT(*) as units_sold,
    SUM(total_amount) as total_revenue,
    ROUND(AVG(unit_price), 2) as avg_price
FROM enriched_sales
GROUP BY product
ORDER BY total_revenue DESC;


-- ============================================
-- QUERY 5: CUSTOMER TIER ANALYSIS
-- ============================================
-- Purpose: Analyze spending patterns by membership tier
-- Business use: Loyalty program effectiveness, customer segmentation

SELECT 
    membership_tier,
    COUNT(DISTINCT customer_id) as customer_count,
    COUNT(*) as transaction_count,
    SUM(total_amount) as total_revenue,
    ROUND(AVG(total_amount), 2) as avg_order_value
FROM enriched_sales
GROUP BY membership_tier
ORDER BY total_revenue DESC;


-- ============================================
-- QUERY 6: MONTHLY SALES TREND
-- ============================================
-- Purpose: Track sales performance over time
-- Business use: Identify seasonal patterns, forecast future sales

SELECT 
    year,
    month,
    COUNT(*) as transaction_count,
    SUM(total_amount) as total_revenue,
    ROUND(AVG(total_amount), 2) as avg_order_value
FROM enriched_sales
GROUP BY year, month
ORDER BY year, month;


-- ============================================
-- QUERY 7: CUSTOMER AGE GROUP ANALYSIS
-- ============================================
-- Purpose: Understand customer demographics and spending
-- Business use: Targeted marketing, product development

SELECT 
    age_group,
    COUNT(DISTINCT customer_id) as customer_count,
    SUM(total_amount) as total_revenue,
    ROUND(AVG(total_amount), 2) as avg_order_value
FROM enriched_sales
GROUP BY age_group
ORDER BY total_revenue DESC;


-- ============================================
-- QUERY 8: REGION + PRODUCT COMBINATION ANALYSIS
-- ============================================
-- Purpose: Identify best-selling products per region
-- Business use: Regional inventory optimization

SELECT 
    region,
    product,
    COUNT(*) as transaction_count,
    SUM(total_amount) as total_revenue
FROM enriched_sales
GROUP BY region, product
ORDER BY total_revenue DESC
LIMIT 20;


-- ============================================
-- QUERY 9: PRE-AGGREGATED SUMMARY TABLE QUERY
-- ============================================
-- Purpose: Fast dashboard queries using pre-computed metrics
-- Why faster: Data already aggregated by Glue ETL job

SELECT 
    region,
    product,
    year,
    month,
    total_revenue,
    transaction_count,
    ROUND(avg_transaction_value, 2) as avg_order
FROM sales_summary
ORDER BY total_revenue DESC
LIMIT 20;


-- ============================================
-- QUERY 10: HIGH-VALUE TRANSACTIONS
-- ============================================
-- Purpose: Identify large orders for special attention
-- Business use: VIP customer service, fraud detection

SELECT 
    transaction_id,
    date,
    customer_id,
    product,
    total_amount,
    membership_tier
FROM enriched_sales
WHERE total_amount > 1000
ORDER BY total_amount DESC
LIMIT 50;


-- ============================================
-- QUERY 11: DATE FILTERING EXAMPLE
-- ============================================
-- Purpose: Filter transactions by specific date
-- Note: Date column contains full timestamp with nanoseconds
-- Solution: Use substring to extract date portion (YYYY-MM-DD)

SELECT 
    transaction_id,
    date,
    customer_id,
    product,
    total_amount,
    region
FROM enriched_sales
WHERE substring(date, 1, 10) = '2025-10-15'
LIMIT 10;


-- ============================================
-- QUERY 12: DATE RANGE FILTERING
-- ============================================
-- Purpose: Analyze transactions within a date range
-- Example: All October 2025 transactions

SELECT 
    transaction_id,
    date,
    total_amount,
    product,
    region
FROM enriched_sales
WHERE substring(date, 1, 10) BETWEEN '2025-10-01' AND '2025-10-31'
ORDER BY total_amount DESC
LIMIT 20;


-- ============================================
-- PERFORMANCE NOTES
-- ============================================
-- Data Format: Parquet (columnar, compressed)
-- Partitioning: By year and month (faster queries when filtering by date)
-- Cost: ~$0.000005 per query (essentially free under free tier)

-- ============================================
-- OPTIMIZATION TIPS
-- ============================================
-- 1. Always filter by partition columns (year, month) when possible
-- 2. Use summary table for dashboard queries (pre-aggregated)
-- 3. SELECT only needed columns (not SELECT *)
-- 4. Use LIMIT when exploring data
-- 5. Use substring(date, 1, 10) for date filtering (most efficient)
-- 6. Consider creating views for frequently used queries



