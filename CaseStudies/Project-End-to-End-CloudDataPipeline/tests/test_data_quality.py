"""
Data Quality Testing Framework for AWS ETL Pipeline
Validates data integrity, completeness, and business rules
Fixed version for split database setup
"""

import boto3
import pandas as pd
import pytest
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
RAW_DATA_BUCKET = os.getenv('RAW_DATA_BUCKET', 'michel-raw-data-pipeline-project1')
PROCESSED_DATA_BUCKET = os.getenv('PROCESSED_DATA_BUCKET', 'michel-processed-data-pipeline-project1')

# DATABASE CONFIGURATION - TWO SEPARATE DATABASES
RAW_DATABASE_NAME = os.getenv('RAW_DATABASE_NAME', 'project1_sales_pipeline_db_december2025')
PROCESSED_DATABASE_NAME = os.getenv('PROCESSED_DATABASE_NAME', 'project1_sales_analytics_db')

ATHENA_OUTPUT_BUCKET = os.getenv('ATHENA_OUTPUT_BUCKET', 'michel-athena-results-pipeline-project1')

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=AWS_REGION)
athena_client = boto3.client('athena', region_name=AWS_REGION)
glue_client = boto3.client('glue', region_name=AWS_REGION)


class DataQualityChecker:
    """Comprehensive data quality validation framework"""
    
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
        
    def run_athena_query(self, query: str, database: str = None) -> pd.DataFrame:
        """Execute Athena query and return results as DataFrame
        
        Args:
            query: SQL query to execute
            database: Database name (defaults to RAW_DATABASE_NAME if not specified)
        """
        if database is None:
            database = RAW_DATABASE_NAME
            
        try:
            response = athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': database},
                ResultConfiguration={
                    'OutputLocation': f's3://{ATHENA_OUTPUT_BUCKET}/quality-checks/'
                }
            )
            
            query_execution_id = response['QueryExecutionId']
            
            # Wait for query to complete
            max_attempts = 30
            for attempt in range(max_attempts):
                status = athena_client.get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                state = status['QueryExecution']['Status']['State']
                
                if state == 'SUCCEEDED':
                    break
                elif state in ['FAILED', 'CANCELLED']:
                    raise Exception(f"Query {state}: {status['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')}")
                
                import time
                time.sleep(2)
            
            # Get results
            results = athena_client.get_query_results(
                QueryExecutionId=query_execution_id
            )
            
            # Convert to DataFrame
            rows = results['ResultSet']['Rows']
            if len(rows) <= 1:
                return pd.DataFrame()
            
            headers = [col['VarCharValue'] for col in rows[0]['Data']]
            data = []
            for row in rows[1:]:
                data.append([col.get('VarCharValue', None) for col in row['Data']])
            
            return pd.DataFrame(data, columns=headers)
            
        except Exception as e:
            logger.error(f"Athena query failed: {e}")
            raise
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log individual test results"""
        result = {
            'test_name': test_name,
            'passed': passed,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.test_results.append(result)
        
        if not passed:
            self.failed_tests.append(test_name)
            logger.error(f"❌ FAILED: {test_name} - {details}")
        else:
            logger.info(f"✅ PASSED: {test_name}")
    
    def get_test_summary(self) -> Dict:
        """Generate test execution summary"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['passed'])
        failed = total - passed
        
        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'success_rate': f"{(passed/total*100):.2f}%" if total > 0 else "0%",
            'failed_tests': self.failed_tests,
            'detailed_results': self.test_results
        }


# ==================== Test Suite ====================

@pytest.fixture(scope="session")
def quality_checker():
    """Fixture to initialize quality checker"""
    return DataQualityChecker()


class TestRawDataQuality:
    """Test suite for raw data validation - Uses RAW_DATABASE_NAME"""
    
    def test_raw_data_files_exist(self, quality_checker):
        """Verify raw data files are present in S3"""
        try:
            response = s3_client.list_objects_v2(
                Bucket=RAW_DATA_BUCKET,
                Prefix='input/'
            )
            
            files = [obj['Key'] for obj in response.get('Contents', [])]
            required_files = ['input/sales_data.csv', 'input/customer_demographics.json']
            
            missing_files = [f for f in required_files if f not in files]
            
            passed = len(missing_files) == 0
            details = f"Found {len(files)} files. Missing: {missing_files}" if not passed else f"All {len(required_files)} required files present"
            
            quality_checker.log_test_result(
                'raw_data_files_exist',
                passed,
                details
            )
            assert passed, details
            
        except Exception as e:
            quality_checker.log_test_result('raw_data_files_exist', False, str(e))
            pytest.fail(str(e))
    
    def test_sales_data_row_count(self, quality_checker):
        """Verify sales data has expected minimum row count"""
        try:
            query = "SELECT COUNT(*) as row_count FROM sales_data_csv"
            df = quality_checker.run_athena_query(query, database=RAW_DATABASE_NAME)
            
            row_count = int(df.iloc[0]['row_count'])
            min_expected = 1000
            
            passed = row_count >= min_expected
            details = f"Row count: {row_count}, Expected minimum: {min_expected}"
            
            quality_checker.log_test_result(
                'sales_data_row_count',
                passed,
                details
            )
            assert passed, details
            
        except Exception as e:
            quality_checker.log_test_result('sales_data_row_count', False, str(e))
            pytest.fail(str(e))
    
    def test_no_null_critical_fields(self, quality_checker):
        """Verify critical fields have no NULL values"""
        try:
            critical_fields = ['transaction_id', 'customer_id', 'product', 'total_amount']
            
            for field in critical_fields:
                query = f"""
                SELECT COUNT(*) as null_count 
                FROM sales_data_csv 
                WHERE {field} IS NULL OR CAST({field} AS VARCHAR) = ''
                """
                df = quality_checker.run_athena_query(query, database=RAW_DATABASE_NAME)
                null_count = int(df.iloc[0]['null_count'])
                
                passed = null_count == 0
                details = f"Field '{field}': {null_count} NULL values found"
                
                quality_checker.log_test_result(
                    f'no_null_{field}',
                    passed,
                    details
                )
                assert passed, details
                
        except Exception as e:
            quality_checker.log_test_result('no_null_critical_fields', False, str(e))
            pytest.fail(str(e))
    
    def test_transaction_id_uniqueness(self, quality_checker):
        """Verify transaction IDs are unique"""
        try:
            query = """
            SELECT COUNT(*) as total_count, 
                   COUNT(DISTINCT transaction_id) as unique_count
            FROM sales_data_csv
            """
            df = quality_checker.run_athena_query(query, database=RAW_DATABASE_NAME)
            
            total = int(df.iloc[0]['total_count'])
            unique = int(df.iloc[0]['unique_count'])
            
            passed = total == unique
            details = f"Total: {total}, Unique: {unique}, Duplicates: {total - unique}"
            
            quality_checker.log_test_result(
                'transaction_id_uniqueness',
                passed,
                details
            )
            assert passed, details
            
        except Exception as e:
            quality_checker.log_test_result('transaction_id_uniqueness', False, str(e))
            pytest.fail(str(e))
    
    def test_amount_validity(self, quality_checker):
        """Verify transaction amounts are within valid range"""
        try:
            query = """
            SELECT COUNT(*) as invalid_count
            FROM sales_data_csv
            WHERE CAST(total_amount AS DOUBLE) <= 0 
               OR CAST(total_amount AS DOUBLE) > 100000
            """
            df = quality_checker.run_athena_query(query, database=RAW_DATABASE_NAME)
            invalid_count = int(df.iloc[0]['invalid_count'])
            
            passed = invalid_count == 0
            details = f"{invalid_count} transactions with invalid amounts (<=0 or >100,000)"
            
            quality_checker.log_test_result(
                'amount_validity',
                passed,
                details
            )
            assert passed, details
            
        except Exception as e:
            quality_checker.log_test_result('amount_validity', False, str(e))
            pytest.fail(str(e))
    
    def test_date_format_validity(self, quality_checker):
        """Verify dates are in valid format"""
        try:
            query = """
            SELECT COUNT(*) as invalid_dates
            FROM sales_data_csv
            WHERE date IS NULL 
               OR LENGTH(CAST(date AS VARCHAR)) < 10
            """
            df = quality_checker.run_athena_query(query, database=RAW_DATABASE_NAME)
            invalid_count = int(df.iloc[0]['invalid_dates'])
            
            passed = invalid_count == 0
            details = f"{invalid_count} records with invalid date format"
            
            quality_checker.log_test_result(
                'date_format_validity',
                passed,
                details
            )
            assert passed, details
            
        except Exception as e:
            quality_checker.log_test_result('date_format_validity', False, str(e))
            pytest.fail(str(e))


class TestProcessedDataQuality:
    """Test suite for processed/enriched data validation - Uses PROCESSED_DATABASE_NAME"""
    
    def test_enriched_table_exists(self, quality_checker):
        """Verify enriched_sales table exists in Glue catalog"""
        try:
            response = glue_client.get_table(
                DatabaseName=PROCESSED_DATABASE_NAME,
                Name='enriched_sales'
            )
            
            passed = response is not None
            details = f"Table 'enriched_sales' found with {len(response['Table']['StorageDescriptor']['Columns'])} columns"
            
            quality_checker.log_test_result(
                'enriched_table_exists',
                passed,
                details
            )
            assert passed, details
            
        except glue_client.exceptions.EntityNotFoundException:
            quality_checker.log_test_result(
                'enriched_table_exists',
                False,
                "Table 'enriched_sales' not found in catalog"
            )
            pytest.fail("Enriched table does not exist")
        except Exception as e:
            quality_checker.log_test_result('enriched_table_exists', False, str(e))
            pytest.fail(str(e))
    
    def test_data_enrichment_join_success(self, quality_checker):
        """Verify join with customer data was successful"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_records,
                SUM(CASE WHEN age_group IS NOT NULL THEN 1 ELSE 0 END) as enriched_records
            FROM enriched_sales
            """
            df = quality_checker.run_athena_query(query, database=PROCESSED_DATABASE_NAME)
            
            total = int(df.iloc[0]['total_records'])
            enriched = int(df.iloc[0]['enriched_records'])
            enrichment_rate = (enriched / total * 100) if total > 0 else 0
            
            passed = enrichment_rate >= 80
            details = f"Enrichment rate: {enrichment_rate:.2f}% ({enriched}/{total})"
            
            quality_checker.log_test_result(
                'data_enrichment_success',
                passed,
                details
            )
            assert passed, details
            
        except Exception as e:
            quality_checker.log_test_result('data_enrichment_success', False, str(e))
            pytest.fail(str(e))
    
    def test_partition_coverage(self, quality_checker):
        """Verify data is properly partitioned by year/month"""
        try:
            query = """
            SELECT DISTINCT year, month
            FROM enriched_sales
            ORDER BY year, month
            """
            df = quality_checker.run_athena_query(query, database=PROCESSED_DATABASE_NAME)
            
            partition_count = len(df)
            
            passed = partition_count >= 3
            details = f"Found {partition_count} year/month partitions"
            
            quality_checker.log_test_result(
                'partition_coverage',
                passed,
                details
            )
            assert passed, details
            
        except Exception as e:
            quality_checker.log_test_result('partition_coverage', False, str(e))
            pytest.fail(str(e))
    
    def test_aggregation_accuracy(self, quality_checker):
        """Verify sales_summary aggregations match raw data"""
        try:
            # Get total from raw data
            raw_query = "SELECT SUM(CAST(total_amount AS DOUBLE)) as total FROM sales_data_csv"
            raw_df = quality_checker.run_athena_query(raw_query, database=RAW_DATABASE_NAME)
            raw_total = float(raw_df.iloc[0]['total'])
            
            # Get total from summary table
            summary_query = "SELECT SUM(CAST(total_revenue AS DOUBLE)) as total FROM sales_summary"
            summary_df = quality_checker.run_athena_query(summary_query, database=PROCESSED_DATABASE_NAME)
            summary_total = float(summary_df.iloc[0]['total'])
            
            # Allow 1% tolerance
            diff_percentage = abs(raw_total - summary_total) / raw_total * 100
            passed = diff_percentage < 1.0
            
            details = f"Raw total: ${raw_total:,.2f}, Summary total: ${summary_total:,.2f}, Diff: {diff_percentage:.4f}%"
            
            quality_checker.log_test_result(
                'aggregation_accuracy',
                passed,
                details
            )
            assert passed, details
            
        except Exception as e:
            quality_checker.log_test_result('aggregation_accuracy', False, str(e))
            pytest.fail(str(e))


class TestBusinessRules:
    """Test suite for business logic validation"""
    
    def test_regional_distribution(self, quality_checker):
        """Verify data contains expected regions"""
        try:
            query = """
            SELECT DISTINCT region 
            FROM sales_data_csv
            ORDER BY region
            """
            df = quality_checker.run_athena_query(query, database=RAW_DATABASE_NAME)
            
            regions = set(df['region'].tolist())
            expected_regions = {'North', 'South', 'East', 'West'}
            
            passed = expected_regions.issubset(regions)
            details = f"Found regions: {regions}, Expected: {expected_regions}"
            
            quality_checker.log_test_result(
                'regional_distribution',
                passed,
                details
            )
            assert passed, details
            
        except Exception as e:
            quality_checker.log_test_result('regional_distribution', False, str(e))
            pytest.fail(str(e))
    
    def test_revenue_consistency(self, quality_checker):
        """Verify total_amount = quantity * unit_price"""
        try:
            query = """
            SELECT COUNT(*) as inconsistent_count
            FROM sales_data_csv
            WHERE ABS(
                CAST(total_amount AS DOUBLE) - 
                (CAST(quantity AS DOUBLE) * CAST(unit_price AS DOUBLE))
            ) > 0.01
            """
            df = quality_checker.run_athena_query(query, database=RAW_DATABASE_NAME)
            inconsistent = int(df.iloc[0]['inconsistent_count'])
            
            passed = inconsistent == 0
            details = f"{inconsistent} records with calculation inconsistencies"
            
            quality_checker.log_test_result(
                'revenue_consistency',
                passed,
                details
            )
            assert passed, details
            
        except Exception as e:
            quality_checker.log_test_result('revenue_consistency', False, str(e))
            pytest.fail(str(e))
    
    def test_customer_tier_values(self, quality_checker):
        """Verify customer tiers contain only valid values"""
        try:
            query = """
            SELECT DISTINCT membership_tier
            FROM customer_demographics_json
            WHERE membership_tier IS NOT NULL
            """
            df = quality_checker.run_athena_query(query, database=RAW_DATABASE_NAME)
            
            tiers = set(df['membership_tier'].tolist())
            valid_tiers = {'Bronze', 'Silver', 'Gold', 'Platinum'}
            
            invalid_tiers = tiers - valid_tiers
            passed = len(invalid_tiers) == 0
            
            details = f"Found tiers: {tiers}. Invalid: {invalid_tiers}" if invalid_tiers else f"All tiers valid: {tiers}"
            
            quality_checker.log_test_result(
                'customer_tier_values',
                passed,
                details
            )
            assert passed, details
            
        except Exception as e:
            quality_checker.log_test_result('customer_tier_values', False, str(e))
            pytest.fail(str(e))


# ==================== Test Report Generation ====================

@pytest.fixture(scope="session", autouse=True)
def generate_report(request, quality_checker):
    """Generate test report at end of session"""
    yield
    
    # Generate summary
    summary = quality_checker.get_test_summary()
    
    # Print to console
    print("\n" + "="*60)
    print("DATA QUALITY TEST SUMMARY")
    print("="*60)
    print(f"Total Tests:    {summary['total_tests']}")
    print(f"Passed:         {summary['passed']}")
    print(f"Failed:         {summary['failed']}")
    print(f"Success Rate:   {summary['success_rate']}")
    print("="*60)
    
    if summary['failed_tests']:
        print("\nFailed Tests:")
        for test in summary['failed_tests']:
            print(f"  ❌ {test}")
    
    # Save detailed report
    report_path = 'test_reports/data_quality_report.json'
    os.makedirs('test_reports', exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_path}\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
    

