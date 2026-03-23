"""
Email Test Data Generator for UAT
Automates creation of Excel files with fabricated email test data
"""
 
import openpyxl
from openpyxl import Workbook
from datetime import datetime
 
 
# ==================== CONFIGURATION SECTION ====================
# Modify these values before running the script
 
CONFIG = {
    # ID range
    "id_start": 1,
    "id_end": 9,
    
    # Message date (format: YYYY/MM/DD)
    "message_date": "2026/03/20",
    
    # Sender and participants (same for all rows)
    "sender": "sender@company.com",
    "participants": "recipient1@company.com,recipient2@company.com",
    
    # Output filename
    "output_filename": "email_test_data.xlsx",
}
 
# Test scenarios for Subject column
# The script will cycle through these scenarios to populate rows
# Format: ExpectedResult_EmailOrChat_RuleNumber_FeatureNumber_PatternId_RowNumber
TEST_SCENARIOS = [
    {"result": "Alert", "email_or_chat": "Email", "rule": "6087", "feature": "7188", "pattern": "87"},
    {"result": "NoAlert", "email_or_chat": "Email", "rule": "6087", "feature": "7188", "pattern": "87"},
    {"result": "Alert", "email_or_chat": "Email", "rule": "6062", "feature": "7229", "pattern": "16"},
    {"result": "NoAlert", "email_or_chat": "Email", "rule": "6062", "feature": "7229", "pattern": "16"},
]
 
# ==================== END CONFIGURATION ====================
 
 
def generate_message_id(row_num):
    """Generate message_id in format M001, M002, etc."""
    return f"M{row_num:03d}"
 
 
def generate_subject(scenario, row_num):
    """Generate Subject in format: ExpectedResult_EmailOrChat_RuleNumber_FeatureNumber_PatternId_RowNumber"""
    return (f"{scenario['result']}_"
            f"{scenario['email_or_chat']}_"
            f"Rule{scenario['rule']}_"
            f"Feature{scenario['feature']}_"
            f"PattId{scenario['pattern']}_"
            f"Row{row_num}")
 
 
def generate_excel_data(config, test_scenarios):
    """
    Generate test data based on configuration
    Returns list of dictionaries, one per row
    """
    data = []
    id_start = config["id_start"]
    id_end = config["id_end"]
    num_rows = id_end - id_start + 1
    
    for i in range(num_rows):
        row_num = id_start + i
        
        # Cycle through test scenarios
        scenario = test_scenarios[i % len(test_scenarios)]
        
        row_data = {
            "id": row_num,
            "message_date": config["message_date"],
            "attachments": "",
            "html": "",
            "message_id": generate_message_id(row_num),
            "body": "",
            "Subject": generate_subject(scenario, row_num),
            "sender": config["sender"],
            "participants": config["participants"],
        }
        
        data.append(row_data)
    
    return data
 
 
def write_to_excel(data, filename):
    """
    Write data to Excel file with specified column order
    """
    # Create workbook and select active sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Email Test Data"
    
    # Define column headers in the exact order required
    headers = ["id", "message_date", "attachments", "html", "message_id", 
               "body", "Subject", "sender", "participants"]
    
    # Write headers
    ws.append(headers)
    
    # Write data rows
    for row_data in data:
        row_values = [row_data[header] for header in headers]
        ws.append(row_values)
    
    # Save workbook
    wb.save(filename)
    print(f"✓ Excel file created successfully: {filename}")
    print(f"✓ Total rows generated: {len(data)}")
 
 
def main():
    """Main execution function"""
    print("=" * 60)
    print("Email Test Data Generator")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  ID Range: {CONFIG['id_start']} to {CONFIG['id_end']}")
    print(f"  Message Date: {CONFIG['message_date']}")
    print(f"  Sender: {CONFIG['sender']}")
    print(f"  Participants: {CONFIG['participants']}")
    print(f"  Output File: {CONFIG['output_filename']}")
    print(f"  Test Scenarios: {len(TEST_SCENARIOS)} defined")
    print("\nGenerating data...")
    
    # Generate data
    data = generate_excel_data(CONFIG, TEST_SCENARIOS)
    
    # Write to Excel
    write_to_excel(data, CONFIG['output_filename'])
    
    print("\n" + "=" * 60)
    print("Generation Complete!")
    print("=" * 60)

