"""
Chat Message Test Data Generator for UAT
Automates creation of Excel files with fabricated chat test data
"""
 
import openpyxl
from openpyxl import Workbook
from datetime import datetime, timedelta
 
 
# ==================== CONFIGURATION SECTION ====================
# Modify these values before running the script
 
CONFIG = {
    # Total number of rows to generate
    "total_rows": 9,
    
    # Rows per conversation (must sum to total_rows)
    # Each conversation must have minimum 2 rows
    # Example: [2, 2, 2, 3] creates M001(2 rows), M002(2 rows), M003(2 rows), M004(3 rows)
    "rows_per_conversation": [2, 2, 2, 3],
    
    # Starting message time
    "start_date": "2026/03/18",  # Format: YYYY/MM/DD
    "start_hour": 11,            # 24-hour format (0-23)
    "start_minute": 6,           # Starting minute
    "start_second": 7,           # Starting second
    "start_period": "AM",        # AM or PM
    
    # Sender emails (will cycle through these)
    "sender_emails": [
        "email1@gmail.com",
        "email2@gmail.com"
    ],
    
    # Participants (same for all rows, comma-separated with no spaces)
    "participants": "email1@gmail.com,email2@gmail.com",
    
    # Output filename
    "output_filename": "chat_test_data.xlsx",
}
 
# Test scenarios for Subject column
# Format: ExpectedResult_Chat_RuleNumber_FeatureNumber_PatternId_RowNumber
TEST_SCENARIOS = [
    {"result": "Alert", "rule": "6087", "feature": "7188", "pattern": "87"},
    {"result": "NoAlert", "rule": "6087", "feature": "7188", "pattern": "87"},
    {"result": "Alert", "rule": "6062", "feature": "7229", "pattern": "16"},
    {"result": "NoAlert", "rule": "6062", "feature": "7229", "pattern": "16"},
]
 
# ==================== END CONFIGURATION ====================
 
 
def validate_configuration(config):
    """Validate that configuration is correct"""
    total_rows = config["total_rows"]
    rows_per_conv = config["rows_per_conversation"]
    
    # Check if rows_per_conversation sums to total_rows
    if sum(rows_per_conv) != total_rows:
        raise ValueError(f"rows_per_conversation {rows_per_conv} sums to {sum(rows_per_conv)}, but total_rows is {total_rows}")
    
    # Check minimum 2 rows per conversation
    if any(rows < 2 for rows in rows_per_conv):
        raise ValueError("Each conversation must have minimum 2 rows")
    
    print("✓ Configuration validated successfully")
 
 
def generate_conversation_id(conv_num):
    """Generate conversation_id in format M001, M002, etc."""
    return f"M{conv_num:03d}"
 
 
def increment_time(current_time):
    """
    Increment time by 1 minute
    Handles rollover to next hour automatically
    """
    return current_time + timedelta(minutes=1)
 
 
def format_time_12hr(dt):
    """Format datetime to YYYY/MM/DD HH:MM:SS AM/PM"""
    return dt.strftime("%Y/%m/%d %I:%M:%S %p")
 
 
def generate_subject(scenario, row_num):
    """Generate Subject in format: ExpectedResult_Chat_RuleNumber_FeatureNumber_PatternId_RowNumber"""
    return (f"{scenario['result']}_"
            f"Chat_"  # Always "Chat" for chat messages
            f"Rule{scenario['rule']}_"
            f"Feature{scenario['feature']}_"
            f"PattId{scenario['pattern']}_"
            f"Row{row_num}")
 
 
def create_starting_datetime(config):
    """Create starting datetime from configuration"""
    date_str = config["start_date"]
    hour = config["start_hour"]
    minute = config["start_minute"]
    second = config["start_second"]
    
    # Parse date
    year, month, day = map(int, date_str.split('/'))
    
    # Create datetime object
    dt = datetime(year, month, day, hour, minute, second)
    
    return dt
 
 
def generate_chat_data(config, test_scenarios):
    """
    Generate chat test data based on configuration
    Returns list of dictionaries, one per row
    """
    data = []
    rows_per_conv = config["rows_per_conversation"]
    sender_emails = config["sender_emails"]
    participants = config["participants"]
    
    # Create starting datetime
    current_time = create_starting_datetime(config)
    
    # Track which conversation we're in
    conv_num = 1
    row_num = 1
    
    # Generate data for each conversation
    for conv_rows in rows_per_conv:
        conv_id = generate_conversation_id(conv_num)
        
        # Generate rows for this conversation
        for i in range(conv_rows):
            # Cycle through test scenarios
            scenario = test_scenarios[(row_num - 1) % len(test_scenarios)]
            
            # Cycle through sender emails
            sender = sender_emails[(row_num - 1) % len(sender_emails)]
            
            row_data = {
                "ID": row_num,
                "Conversation_Id": conv_id,
                "Message Time": format_time_12hr(current_time),
                "Subject": generate_subject(scenario, row_num),
                "Body": "",
                "Sender": sender,
                "Participants": participants,
            }
            
            data.append(row_data)
            
            # Increment time by 1 minute for next row
            current_time = increment_time(current_time)
            row_num += 1
        
        conv_num += 1
    
    return data
 
 
def write_to_excel(data, filename):
    """
    Write data to Excel file with specified column order
    """
    # Create workbook and select active sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Chat Test Data"
    
    # Define column headers in the exact order required
    headers = ["ID", "Conversation_Id", "Message Time", "Subject", 
               "Body", "Sender", "Participants"]
    
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
    print(f"✓ Total conversations: {len(CONFIG['rows_per_conversation'])}")
 
 
def main():
    """Main execution function"""
    print("=" * 60)
    print("Chat Message Test Data Generator")
    print("=" * 60)
    
    # Validate configuration
    try:
        validate_configuration(CONFIG)
    except ValueError as e:
        print(f"\n✗ Configuration Error: {e}")
        return
    
    print(f"\nConfiguration:")
    print(f"  Total Rows: {CONFIG['total_rows']}")
    print(f"  Conversations: {CONFIG['rows_per_conversation']}")
    print(f"  Start Date: {CONFIG['start_date']}")
    print(f"  Start Time: {CONFIG['start_hour']:02d}:{CONFIG['start_minute']:02d}:{CONFIG['start_second']:02d} {CONFIG['start_period']}")
    print(f"  Sender Emails: {CONFIG['sender_emails']}")
    print(f"  Participants: {CONFIG['participants']}")
    print(f"  Output File: {CONFIG['output_filename']}")
    print(f"  Test Scenarios: {len(TEST_SCENARIOS)} defined")
    print("\nGenerating data...")
    
    # Generate data
    data = generate_chat_data(CONFIG, TEST_SCENARIOS)
    
    # Write to Excel
    write_to_excel(data, CONFIG['output_filename'])
    
    print("\n" + "=" * 60)
    print("Generation Complete!")
    print("=" * 60)
