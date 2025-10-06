📜 README.md
# 📖 Bible Quiz Web App

A lightweight **Flask web application** for searching, reviewing, and exporting Bible quiz questions.  
Built for study groups, competitions, and personal learning — with features that make reviewing and managing questions simple and transparent.

---

## ✨ Features

- 🔍 **Search & Filter**  
  Search questions by keyword and filter by chapter.

- ✅ **Checkbox Selection**  
  Choose specific questions to export, with a **Select All** option for convenience.

- 📤 **Excel Export**  
  Export selected questions into a polished Excel workbook with:
  - **Selected Questions** sheet (main export, duplicates highlighted)  
  - **Duplicates Only** sheet (isolated repeats)  
  - **Export Summary** sheet (timestamp, counts, stats)  
  - **Duplicate Review** sheet (grouped dashboard of overlaps)

- 🎨 **Excel Formatting**  
  - Frozen headers  
  - Auto‑sized columns  
  - Filters on all headers  
  - Conditional formatting for duplicates  

- 🛡 **Transparency First**  
  No automatic deletion of duplicates — instead, they’re flagged and grouped for **manual review**.

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/bible-quiz-web.git
cd bible-quiz-web

2. Install Dependencies
It’s best to use a virtual environment:
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt


3. Build the Database
Convert your Excel question bank into a clean SQLite database:
python build_bible_quiz_db.py


This creates bible_quiz.db with all your questions.
4. Run the Web App
python bible_quiz_web.py

Then open http://127.0.0.1:5000 in your browser.

📂 Project Structure
bible-quiz-web/
├── bible_quiz_web.py        # Flask app
├── build_bible_quiz_db.py   # Script to build SQLite DB from Excel
├── bible_quiz.db            # SQLite database (generated)
├── requirements.txt         # Dependencies
└── README.md                # Project documentation


📦 Requirements
- Python 3.8+
- Flask
- pandas
- XlsxWriter
- openpyxl
Install them all with:
pip install -r requirements.txt


🧠 Usage Notes
- Duplicates are never deleted automatically. They’re highlighted and grouped in exports so you can review them manually.
- Verse references are cleaned to avoid Excel’s time formatting quirks (15:34:00 → 15:34).
- Empty answer slots are left blank instead of showing "nan".

🌐 Deployment
You can deploy this app to platforms like:
- Render
- Replit
- Heroku
- Fly.io

🤝 Contributing
Pull requests are welcome! If you’d like to add features (e.g. new export formats, question tagging, or user authentication), feel free to fork and submit improvements.

📜 License
This project is open‑source under the MIT License. See LICENSE for details.

---

👉 To make it a downloadable file on your machine:
1. Open a text editor (VS Code, Notepad++, even Notepad).  
2. Paste the above content.  
3. Save it as **`README.md`** in your project folder.  
4. Commit and push it to GitHub — it will render automatically on your repo’s front page.


