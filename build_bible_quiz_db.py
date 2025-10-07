import pandas as pd
import sqlite3
import os
import re
from pathlib import Path

# === CONFIG ===
data_folder = Path(r"C:\Users\claud\OneDrive\Desktop\NBB_Questions")  # folder with all Excel files
db_path = "bible_quiz.db"

# --- Helper function to clean verse references ---
def clean_reference(val):
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() == "nan":
        return ""
    # Remove trailing :00 or :00.000000 (Excel time artifacts)
    s = re.sub(r":00(\.0+)?$", "", s)
    return s

df_list = []

# 🔹 Loop through all Excel files in the folder
for excel_path in data_folder.glob("*.xlsx"):
    print(f"Processing {excel_path.name}...")
    xls = pd.ExcelFile(excel_path, engine="openpyxl")
    
    for sheet in xls.sheet_names:
        print(f"  - Importing sheet: {sheet}")
        temp_df = xls.parse(sheet, dtype=str)

        # Rename columns to match Flask app
        rename_map = {
            "Question": "correct_answer",   # actual question text
            "Correct Answer": "question",   # actual correct answer
            "Answer B": "answer_b",
            "Answer C": "answer_c",
            "Answer D": "answer_d"
        }
        temp_df = temp_df.rename(columns={k: v for k, v in rename_map.items() if k in temp_df.columns})

        # Add chapter info from sheet name
        temp_df["chapter"] = str(sheet)

        # Ensure all expected columns exist, log if missing
        expected_cols = ["correct_answer", "question", "answer_b", "answer_c", "answer_d"]
        for col in expected_cols:
            if col not in temp_df.columns:
                print(f"    ⚠️ WARNING: Column '{col}' missing in {excel_path.name} / {sheet}. Filling with blanks.")
                temp_df[col] = ""

        # Reorder columns for consistency
        temp_df = temp_df[["chapter", "correct_answer", "question", "answer_b", "answer_c", "answer_d"]]

        # Clean up references and blanks
        for col in expected_cols:
            temp_df[col] = temp_df[col].apply(clean_reference)

        df_list.append(temp_df)

# Combine all sheets from all files
full_df = pd.concat(df_list, ignore_index=True)

# === Build SQLite DB ===
if os.path.exists(db_path):
    os.remove(db_path)  # start fresh

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter TEXT,
        correct_answer TEXT,
        question TEXT,
        answer_b TEXT,
        answer_c TEXT,
        answer_d TEXT
    )
""")

# Insert data
full_df.to_sql("questions", conn, if_exists="append", index=False)

conn.commit()
conn.close()

print(f"✅ Bible quiz database created at {db_path} with {len(full_df)} rows (cleaned references).")

# Optional: preview first few rows to confirm formatting
print(full_df.head())

# Verification
conn = sqlite3.connect("bible_quiz.db")
cur = conn.cursor()
cur.execute("PRAGMA table_info(questions)")
print(cur.fetchall())
conn.close()