"""
Clean Synthetic Patient Data Generator
=======================================
Generates a 500-record patient CSV with zero data quality issues.
Used to demonstrate the framework's 100% quality score state —
showing the dashboard in a healthy, green state for portfolio evidence.

Usage:
    python3 generate_clean_patient_data.py

Output:
    patient_records_batch_clean_001.csv
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(99)  # Different seed from error batch

# --- Configuration ---
TOTAL_RECORDS = 500

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

BLOOD_TYPES  = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
ALLERGIES    = [
    "Penicillin", "Sulfa", "Aspirin", "Codeine", "None",
    "Latex", "Ibuprofen", "Morphine", "Contrast Dye", "None"
]

def random_date(start_year=1940, end_year=2005):
    start = datetime(start_year, 1, 1)
    end   = datetime(end_year, 12, 31)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")

def random_admission():
    base  = datetime(2026, 6, 1)
    return (base + timedelta(days=random.randint(0, 29))).strftime("%Y-%m-%d")

def random_discharge(admission_str):
    admission = datetime.strptime(admission_str, "%Y-%m-%d")
    discharge = admission + timedelta(days=random.randint(1, 10))
    return discharge.strftime("%Y-%m-%d")

def random_vitals():
    return {
        "heart_rate_bpm":        random.randint(60, 100),
        "systolic_bp_mmhg":      random.randint(110, 140),
        "diastolic_bp_mmhg":     random.randint(65, 90),
        "temperature_celsius":   round(random.uniform(36.4, 37.5), 1),
        "oxygen_saturation_pct": random.randint(95, 100),
        "respiratory_rate_bpm":  random.randint(14, 20),
    }

# --- Generate Clean Records ---
# Every record has:
# - Unique MRN
# - All critical fields populated
# - Valid date formats
# - Vital signs within physiological range
# - Discharge date after admission date
# - Realistic patient age (20-85 years)

records  = []
used_mrns = set()

for i in range(1, TOTAL_RECORDS + 1):
    mrn = f"MRN-{20000 + i}"  # Different MRN range from error batch
    used_mrns.add(mrn)

    admission = random_admission()
    discharge = random_discharge(admission)
    vitals    = random_vitals()

    # Generate realistic DOB (age 20-85)
    birth_year = datetime.now().year - random.randint(20, 85)
    birth_month = random.randint(1, 12)
    birth_day   = random.randint(1, 28)
    dob = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"

    records.append({
        "patient_id":            f"P{i:04d}",
        "mrn":                   mrn,
        "date_of_birth":         dob,
        "admission_date":        admission,
        "discharge_date":        discharge,
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

# --- Write CSV ---
fieldnames = [
    "patient_id", "mrn", "date_of_birth", "admission_date",
    "discharge_date", "primary_diagnosis", "attending_physician",
    "heart_rate_bpm", "systolic_bp_mmhg", "diastolic_bp_mmhg",
    "temperature_celsius", "oxygen_saturation_pct", "respiratory_rate_bpm",
    "blood_type", "allergies"
]

output_file = "patient_records_batch_clean_001.csv"
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)

print(f"✅ Generated {output_file}")
print(f"   Total records    : {TOTAL_RECORDS}")
print(f"   Duplicate MRNs   : 0")
print(f"   Missing fields   : 0")
print(f"   Schema violations: 0")
print(f"   Vital anomalies  : 0")
print(f"   Business rules   : 0")
print(f"   Expected quality score: 100%")
