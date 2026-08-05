"""
Synthetic Patient Data Generator
=================================
Generates a realistic 500-record patient CSV for testing the
Patient Data Quality Framework. Embeds known data quality issues
at clinically realistic rates based on AHIMA 2023 benchmarks.

Usage:
    python generate_patient_data.py

Output:
    patient_records_batch_001.csv
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)  # Fixed seed for reproducibility

# --- Configuration ---
TOTAL_RECORDS       = 500
DUPLICATE_MRN_COUNT = 45   # ~9% duplicate rate (AHIMA benchmark: 8-12%)
MISSING_FIELD_COUNT = 30   # ~6% missing critical fields
SCHEMA_VIOLATION_COUNT = 20  # ~4% schema violations
VITAL_ANOMALY_COUNT = 15   # ~3% out-of-range vital signs
BUSINESS_RULE_COUNT = 10   # ~2% business rule violations

# --- Reference Data ---
DIAGNOSES = [
    "Hypertension", "Type 2 Diabetes", "Pneumonia", "Cardiac Arrest",
    "Appendicitis", "Fracture", "Migraine", "Heart Failure", "Sepsis",
    "COPD", "Stroke", "Kidney Disease", "Asthma", "Depression",
    "Anxiety Disorder", "Obesity", "Anemia", "Hypothyroidism",
    "Atrial Fibrillation", "Chronic Back Pain"
]

PHYSICIANS = [
    "Dr. Smith", "Dr. Jones", "Dr. Brown", "Dr. Wilson", "Dr. Davis",
    "Dr. Miller", "Dr. Taylor", "Dr. Anderson", "Dr. Thomas", "Dr. Jackson",
    "Dr. White", "Dr. Harris", "Dr. Martin", "Dr. Garcia", "Dr. Martinez"
]

BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

ALLERGIES = [
    "Penicillin", "Sulfa", "Aspirin", "Codeine", "None",
    "Latex", "Ibuprofen", "Morphine", "Contrast Dye", "None"
]

def random_date(start_year=1940, end_year=2005):
    start = datetime(start_year, 1, 1)
    end   = datetime(end_year, 12, 31)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")

def random_admission():
    base = datetime(2026, 5, 1)
    return (base + timedelta(days=random.randint(0, 59))).strftime("%Y-%m-%d")

def random_discharge(admission_str):
    admission = datetime.strptime(admission_str, "%Y-%m-%d")
    discharge = admission + timedelta(days=random.randint(1, 10))
    return discharge.strftime("%Y-%m-%d")

def random_vitals():
    return {
        "heart_rate_bpm":        random.randint(55, 110),
        "systolic_bp_mmhg":      random.randint(100, 160),
        "diastolic_bp_mmhg":     random.randint(60, 100),
        "temperature_celsius":   round(random.uniform(36.1, 38.5), 1),
        "oxygen_saturation_pct": random.randint(92, 100),
        "respiratory_rate_bpm":  random.randint(12, 22),
    }

# --- Generate Base Records ---
records = []
used_mrns = set()

for i in range(1, TOTAL_RECORDS + 1):
    mrn = f"MRN-{10000 + i}"
    used_mrns.add(mrn)
    admission = random_admission()
    vitals    = random_vitals()

    records.append({
        "patient_id":            f"P{i:04d}",
        "mrn":                   mrn,
        "date_of_birth":         random_date(),
        "admission_date":        admission,
        "discharge_date":        random_discharge(admission),
        "primary_diagnosis":     random.choice(DIAGNOSES),
        "attending_physician":   random.choice(PHYSICIANS),
        "heart_rate_bpm":        vitals["heart_rate_bpm"],
        "systolic_bp_mmhg":      vitals["systolic_bp_mmhg"],
        "diastolic_bp_mmhg":     vitals["diastolic_bp_mmhg"],
        "temperature_celsius":   vitals["temperature_celsius"],
        "oxygen_saturation_pct": vitals["oxygen_saturation_pct"],
        "respiratory_rate_bpm":  vitals["respiratory_rate_bpm"],
        "blood_type":            random.choice(BLOOD_TYPES),
        "allergies":             random.choice(ALLERGIES),
    })

# --- Inject Issue 1: Duplicate MRNs (~9%) ---
# Pick existing MRNs and assign them to new records
existing_mrns = [r["mrn"] for r in records[:DUPLICATE_MRN_COUNT]]
for i, record in enumerate(records[TOTAL_RECORDS - DUPLICATE_MRN_COUNT:]):
    record["mrn"] = existing_mrns[i]

# --- Inject Issue 2: Missing Critical Fields (~6%) ---
missing_field_records = random.sample(range(TOTAL_RECORDS), MISSING_FIELD_COUNT)
missing_fields_cycle  = [
    "date_of_birth",
    "attending_physician",
    "primary_diagnosis",
    "admission_date",
]
for idx, record_idx in enumerate(missing_field_records):
    field = missing_fields_cycle[idx % len(missing_fields_cycle)]
    records[record_idx][field] = ""

# --- Inject Issue 3: Schema Violations (~4%) ---
schema_violation_records = random.sample(
    [i for i in range(TOTAL_RECORDS) if i not in missing_field_records],
    SCHEMA_VIOLATION_COUNT
)
schema_violations_cycle = [
    ("date_of_birth",   "January 5th 1990"),
    ("admission_date",  "June/01/2026"),
    ("heart_rate_bpm",  "seventy-two"),
    ("temperature_celsius", "normal"),
]
for idx, record_idx in enumerate(schema_violation_records):
    field, bad_value = schema_violations_cycle[idx % len(schema_violations_cycle)]
    records[record_idx][field] = bad_value

# --- Inject Issue 4: Out-of-Range Vital Signs (~3%) ---
vital_anomaly_records = random.sample(
    [i for i in range(TOTAL_RECORDS)
     if i not in missing_field_records
     and i not in schema_violation_records],
    VITAL_ANOMALY_COUNT
)
vital_anomalies_cycle = [
    ("heart_rate_bpm",        450),
    ("oxygen_saturation_pct", 110),
    ("systolic_bp_mmhg",      350),
    ("temperature_celsius",   29.0),
    ("respiratory_rate_bpm",  75),
]
for idx, record_idx in enumerate(vital_anomaly_records):
    field, bad_value = vital_anomalies_cycle[idx % len(vital_anomalies_cycle)]
    records[record_idx][field] = bad_value

# --- Inject Issue 5: Business Rule Violations (~2%) ---
business_rule_records = random.sample(
    [i for i in range(TOTAL_RECORDS)
     if i not in missing_field_records
     and i not in schema_violation_records
     and i not in vital_anomaly_records],
    BUSINESS_RULE_COUNT
)
for record_idx in business_rule_records:
    # Discharge before admission
    admission = records[record_idx]["admission_date"]
    if admission and len(admission) == 10:
        try:
            adm_date = datetime.strptime(admission, "%Y-%m-%d")
            records[record_idx]["discharge_date"] = (
                adm_date - timedelta(days=random.randint(1, 5))
            ).strftime("%Y-%m-%d")
        except ValueError:
            pass

# --- Shuffle records so issues are distributed throughout ---
random.shuffle(records)

# --- Write CSV ---
fieldnames = [
    "patient_id", "mrn", "date_of_birth", "admission_date",
    "discharge_date", "primary_diagnosis", "attending_physician",
    "heart_rate_bpm", "systolic_bp_mmhg", "diastolic_bp_mmhg",
    "temperature_celsius", "oxygen_saturation_pct", "respiratory_rate_bpm",
    "blood_type", "allergies"
]

output_file = "patient_records_batch_001.csv"
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)

print(f"✅ Generated {output_file}")
print(f"   Total records:       {TOTAL_RECORDS}")
print(f"   Duplicate MRNs:      {DUPLICATE_MRN_COUNT} records (~9%)")
print(f"   Missing fields:      {MISSING_FIELD_COUNT} records (~6%)")
print(f"   Schema violations:   {SCHEMA_VIOLATION_COUNT} records (~4%)")
print(f"   Vital anomalies:     {VITAL_ANOMALY_COUNT} records (~3%)")
print(f"   Business rule violations: {BUSINESS_RULE_COUNT} records (~2%)")
print(f"   Clean records:       ~{TOTAL_RECORDS - DUPLICATE_MRN_COUNT - MISSING_FIELD_COUNT - SCHEMA_VIOLATION_COUNT - VITAL_ANOMALY_COUNT - BUSINESS_RULE_COUNT}")
