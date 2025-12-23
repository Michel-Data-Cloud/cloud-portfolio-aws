"""
AWS Glue ETL Job - Sales Data Pipeline
Purpose: Transform raw sales and customer data into analytics-ready datasets
Author: Jack
Date: December 2025

This script:
1. Reads raw sales (CSV) and customer (JSON) data from Glue Data Catalog
2. Joins sales transactions with customer demographics
3. Creates aggregated summaries (revenue by region, product, time period)
4. Writes processed data to S3 as Parquet files (compressed format for fast querying)
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, sum, count, avg, year, month, dayofmonth

# Initialize Glue context
# ========== STEP 1: INITIALIZE AWS GLUE JOB ==========
# Get job name from command-line arguments (AWS Glue passes this automatically)
args = getResolvedOptions(sys.argv, ['JOB_NAME'])

# Create Spark context (engine for distributed data processing)
sc = SparkContext()

# Create Glue context (wrapper around Spark with AWS integrations)
glueContext = GlueContext(sc)

# Get Spark session (interface for working with DataFrames)
spark = glueContext.spark_session

# Initialize Glue job for tracking and monitoring
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print("========== Starting ETL Job ==========")

# ========== STEP 2: READ DATA FROM GLUE DATA CATALOG ==========
# Read sales data (CSV file we uploaded to S3)
# Glue automatically knows the schema from the crawler we ran
print("Reading sales data...")
sales_data = glueContext.create_dynamic_frame.from_catalog(
    database="project1_sales_pipeline_db_december2025", # The Glue database I created
    table_name="sales_data_csv"                         # Table name from crawler
)
print(f"Sales records loaded: {sales_data.count()}")

# Read customer demographics (JSON file we uploaded to S3)
print("Reading customer data from Glue Data Catalog...")
customer_data = glueContext.create_dynamic_frame.from_catalog(
    database="project1_sales_pipeline_db_december2025",
    table_name="customer_demographics_json"             # Table name from crawler
)
print(f"Customer records loaded: {customer_data.count()}")

# ========== STEP 3: CONVERT TO SPARK DATAFRAMES ==========
# DynamicFrames are AWS Glue's special format
# Convert to standard Spark DataFrames for easier transformations
sales_df = sales_data.toDF()
customer_df = customer_data.toDF()

print("Data loaded successfully!")
print("Sales schema:")
sales_df.printSchema() # Shows column names and data types
print("Customer schema:")
customer_df.printSchema()

# ========== STEP 4: TRANSFORMATION 1 - JOIN SALES WITH CUSTOMER DATA ==========
# Business goal: Enrich sales transactions with customer information
# This lets us analyze sales by age group, membership tier, etc.
print("========== Joining sales with customer data ==========")
enriched_df = sales_df.join(customer_df, on="customer_id", how="left")
print(f"Enriched records created: {enriched_df.count()}")

# ========== STEP 5: TRANSFORMATION 2 - ADD DATE COMPONENTS ==========
# Extract year, month, day from transaction date
# Purpose: Enables partitioning for faster queries and organization
print("========== Adding date components ==========")
enriched_df = enriched_df.withColumn("year", year(col("date"))) \
                         .withColumn("month", month(col("date"))) \
                         .withColumn("day", dayofmonth(col("date")))

# Show sample of enriched data (helps verify transformations worked)
print("Sample enriched data:")
enriched_df.show(5, truncate=False)

# ========== STEP 6: TRANSFORMATION 3 - CREATE AGGREGATED SUMMARY ==========
# Business goal: Calculate key metrics for dashboards and reporting
# Groups transactions by region, product, and time period
# Calculates: total revenue, transaction count, average order value
print("========== Creating sales summary ==========")
summary_df = enriched_df.groupBy("region", "product", "year", "month").agg(
    sum("total_amount").alias("total_revenue"),
    count("transaction_id").alias("transaction_count"),
    avg("total_amount").alias("avg_transaction_value")
)
print(f"Summary records created: {summary_df.count()}")

# Show sample summary data
print("Sample summary data:")
summary_df.show(10, truncate=False)

# ========== STEP 7: CONVERT BACK TO DYNAMICFRAMES ==========
# AWS Glue's write functions work with DynamicFrames, not DataFrames
# Convert our transformed DataFrames back to DynamicFrames
from awsglue.dynamicframe import DynamicFrame
enriched_dynamic = DynamicFrame.fromDF(enriched_df, glueContext, "enriched_dynamic")
summary_dynamic = DynamicFrame.fromDF(summary_df, glueContext, "summary_dynamic")

# ========== STEP 8: WRITE ENRICHED DATA TO S3 ==========
# Save the full enriched dataset (all transactions with customer info)
# Format: Parquet (columnar format, 10x smaller than CSV, much faster to query)
# Partitioning: By year/month (makes queries like "show me October 2025" super fast)
print("========== Writing enriched data to S3 (Parquet format) ==========")
glueContext.write_dynamic_frame.from_options(
    frame=enriched_dynamic,
    connection_type="s3",
    connection_options={
        "path": "s3://michel-processed-data-pipeline-project1/enriched/",
        "partitionKeys": ["year", "month"]
    },
    format="parquet",
    format_options={"compression": "snappy"}
)
print("Enriched data written successfully!")

# ========== STEP 9: WRITE SUMMARY DATA TO S3 ==========
# Save the aggregated summary (pre-calculated metrics)
# This is what dashboards will query (much smaller dataset = faster dashboards)
print("========== Writing summary data to S3 (Parquet format) ==========")
glueContext.write_dynamic_frame.from_options(
    frame=summary_dynamic,
    connection_type="s3",
    connection_options={
        "path": "s3://michel-processed-data-pipeline-project1/summary/"
    },
    format="parquet",
    format_options={"compression": "snappy"}
)
print("Summary data written successfully!")

# ========== STEP 10: FINALIZE JOB ==========
# Commit the job (tells AWS Glue the job completed successfully)
# This updates job metrics and logs in CloudWatch
print("========== ETL Job Completed Successfully! ==========")
job.commit()

"""
OUTPUT STRUCTURE IN S3:

jack-processed-data-pipeline-project1/
├── enriched/                           (Full detailed data)
│   ├── year=2025/
│   │   ├── month=9/
│   │   │   └── part-00000.snappy.parquet
│   │   ├── month=10/
│   │   │   └── part-00000.snappy.parquet
│   │   └── month=11/
│   │       └── part-00000.snappy.parquet
│   └── year=2024/...
│
└── summary/                            (Pre-aggregated metrics)
    └── part-00000.snappy.parquet

WHY PARQUET?
- 10x smaller than CSV (compressed columnar format)
- 100x faster to query (only reads columns you need)
- Industry standard for data lakes
- Works seamlessly with Athena, Redshift, QuickSight

WHY PARTITIONING?
- Query "SELECT * WHERE year=2025 AND month=10" only reads ONE folder
- Without partitioning, would scan ALL data
- Saves time and money (Athena charges per data scanned)
"""

