import pandas as pd
import sqlite3
import os
import re

# === CONFIG ===
excel_path = r"C:\Users\claud\OneDrive\Desktop\NBB_Questions\2024 NBBC Spreadsheet_Edited.xlsx"
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

# Load all sheets with dtype=str to force string interpretation
xls = pd.ExcelFile(excel_path, engine="openpyxl")
sheet_names = xls.sheet_names

df_list = []
for sheet in sheet_names:
    temp_df = xls.parse(sheet, dtype=str)

    # Rename columns to match Flask app
    temp_df = temp_df.rename(columns={
        "Question": "correct_answer",   # actual question text
        "Correct Answer": "question",   # actual correct answer
        "Answer B": "answer_b",
        "Answer C": "answer_c",
        "Answer D": "answer_d"
    })

    # Add chapter info from sheet name
    temp_df["chapter"] = str(sheet)

    # Reorder columns for consistency
    temp_df = temp_df[["chapter", "correct_answer", "question", "answer_b", "answer_c", "answer_d"]]

    # Clean up references and blanks
    for col in ["correct_answer", "question", "answer_b", "answer_c", "answer_d"]:
        temp_df[col] = temp_df[col].apply(clean_reference)

    df_list.append(temp_df)

# Combine all sheets
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

#Verification
conn = sqlite3.connect("bible_quiz.db")
cur = conn.cursor()
cur.execute("PRAGMA table_info(questions)")
print(cur.fetchall())
conn.close()