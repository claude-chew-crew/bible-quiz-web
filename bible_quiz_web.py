from flask import Flask, request, render_template_string, send_file
import sqlite3
import pandas as pd
import io
from datetime import datetime

app = Flask(__name__)

# HTML template with search, results, checkboxes, and export options
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Bible Quiz Search</title>
    <style>
        body { font-family: Arial; margin: 40px; background-color: #f9f9f9; }
        h1 { color: #333; }
        form { margin-bottom: 20px; }
        input[type="text"], select { padding: 8px; font-size: 14px; }
        input[type="submit"] { padding: 8px 16px; }
        .result { margin-bottom: 20px; padding: 10px; background: #fff; border: 1px solid #ccc; }
        .question { font-weight: bold; }
        .answer { color: green; }
    </style>
</head>
<body>
    <h1>🔍 Bible Quiz Search</h1>
    <form method="get">
        <input type="text" name="q" placeholder="Enter keyword..." value="{{ query }}">
        <select name="chapter">
            <option value="">-- All Chapters --</option>
            {% for ch in chapters %}
                <option value="{{ ch }}" {% if ch == selected_chapter %}selected{% endif %}>{{ ch }}</option>
            {% endfor %}
        </select>
        <input type="submit" value="Search">
    </form>

    {% if results %}
<form method="post" action="/export">
    <p><strong>{{ results|length }} result(s) found:</strong></p>

    <!-- Select All checkbox -->
    <label>
        <input type="checkbox" id="select-all"> Select All
    </label>
    <br><br>

    {% for row in results %}
        <div class="result">
            <input type="checkbox" name="selected_ids" value="{{ row[0] }}">
            <div class="question">Q: {{ row[2] }}</div>
            <div class="answer">✅ A: {{ row[3] }}</div>
            <ul>
                <li>B: {{ row[4] }}</li>
                <li>C: {{ row[5] }}</li>
                <li>D: {{ row[6] }}</li>
            </ul>
            <div><em>Chapter: {{ row[1] }}</em></div>
        </div>
    {% endfor %}

    <label>
        <input type="checkbox" name="remove_duplicates">
        Remove duplicates (based on Question text)
    </label><br><br>

    <input type="submit" value="Export Selected">
</form>

<!-- Script for Select All -->
<script>
document.getElementById("select-all").addEventListener("change", function(e) {
    const checked = e.target.checked;
    document.querySelectorAll('input[name="selected_ids"]').forEach(cb => {
        cb.checked = checked;
    });
});
</script>
{% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    query = request.args.get("q", "").strip()
    selected_chapter = request.args.get("chapter", "").strip()

    conn = sqlite3.connect("bible_quiz.db")
    cursor = conn.cursor()

    # Get distinct chapters for dropdown
    cursor.execute("SELECT DISTINCT chapter FROM questions ORDER BY chapter")
    chapters = [row[0] for row in cursor.fetchall()]

    # Build query dynamically
    sql = """
        SELECT id, chapter, correct_answer, question, answer_b, answer_c, answer_d
        FROM questions
        WHERE 1=1
    """
    params = []

    if query:
        sql += " AND (correct_answer LIKE ? OR question LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])

    if selected_chapter:
        sql += " AND chapter = ?"
        params.append(selected_chapter)

    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()

    return render_template_string(HTML_TEMPLATE,
                                  results=results,
                                  query=query,
                                  chapters=chapters,
                                  selected_chapter=selected_chapter)

@app.route("/export", methods=["POST"])
def export():
    selected_ids = request.form.getlist("selected_ids")

    if not selected_ids:
        return "⚠️ No questions selected."

    conn = sqlite3.connect("bible_quiz.db")
    cursor = conn.cursor()
    query = f"""
        SELECT chapter, correct_answer, question, answer_b, answer_c, answer_d
        FROM questions
        WHERE id IN ({','.join(['?']*len(selected_ids))})
    """
    cursor.execute(query, selected_ids)
    rows = cursor.fetchall()
    conn.close()

    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=["Chapter", "Question", "Correct Answer", "Answer B", "Answer C", "Answer D"])

    # Flag duplicates by Question text
    df["Is_Duplicate"] = df.duplicated(subset=["Question"], keep=False)

    # Group duplicates together
    df = df.sort_values(by=["Is_Duplicate", "Question"]).reset_index(drop=True)

    # Extract duplicates into a separate DataFrame
    duplicates_df = df[df["Is_Duplicate"] == True].copy()

    # Check if user wants to remove duplicates
    remove_dupes = request.form.get("remove_duplicates") == "on"
    if remove_dupes:
        df = df.drop_duplicates(subset=["Question"])

    # Prepare summary stats with timestamp
    summary_data = {
        "Export Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Total Selected": [len(rows)],
        "Unique Questions": [df["Question"].nunique()],
        "Duplicate Count": [len(duplicates_df)],
        "Duplicates Removed": ["Yes" if remove_dupes else "No"]
    }
    summary_df = pd.DataFrame(summary_data)

    # Build Duplicate Review dashboard
    review_df = (
        df.groupby("Question")
          .agg(
              Count=("Question", "size"),
              Chapters=("Chapter", lambda x: ", ".join(sorted(set(x))))
          )
          .reset_index()
    )
    review_df = review_df[review_df["Count"] > 1]

    # Write to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        red_fill = workbook.add_format({"bg_color": "#FFC7CE"})

        # --- Main sheet ---
        df.to_excel(writer, index=False, sheet_name="Selected Questions")
        ws = writer.sheets["Selected Questions"]
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(df), len(df.columns)-1)
        last_row = len(df) + 1
        ws.conditional_format(f"B2:B{last_row}", {"type": "duplicate", "format": red_fill})
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            ws.set_column(i, i, max_len)

        # --- Duplicates-only sheet ---
        if not duplicates_df.empty:
            duplicates_df.to_excel(writer, index=False, sheet_name="Duplicates Only")
            dup_ws = writer.sheets["Duplicates Only"]
            dup_ws.freeze_panes(1, 0)
            dup_ws.autofilter(0, 0, len(duplicates_df), len(duplicates_df.columns)-1)
            dup_last_row = len(duplicates_df) + 1
            dup_ws.conditional_format(f"A2:F{dup_last_row}", {"type": "no_blanks", "format": red_fill})
            for i, col in enumerate(duplicates_df.columns):
                max_len = max(duplicates_df[col].astype(str).map(len).max(), len(col)) + 2
                dup_ws.set_column(i, i, max_len)

        # --- Summary sheet ---
        summary_df.to_excel(writer, index=False, sheet_name="Export Summary")
        sum_ws = writer.sheets["Export Summary"]
        sum_ws.freeze_panes(1, 0)
        sum_ws.autofilter(0, 0, len(summary_df), len(summary_df.columns)-1)
        for i, col in enumerate(summary_df.columns):
            max_len = max(summary_df[col].astype(str).map(len).max(), len(col)) + 2
            sum_ws.set_column(i, i, max_len)

        # --- Duplicate Review sheet ---
        if not review_df.empty:
            review_df.to_excel(writer, index=False, sheet_name="Duplicate Review")
            rev_ws = writer.sheets["Duplicate Review"]
            rev_ws.freeze_panes(1, 0)
            rev_ws.autofilter(0, 0, len(review_df), len(review_df.columns)-1)
            rev_last_row = len(review_df) + 1
            rev_ws.conditional_format(f"B2:B{rev_last_row}", {
                "type": "cell",
                "criteria": ">",
                "value": 1,
                "format": red_fill
            })
            for i, col in enumerate(review_df.columns):
                max_len = max(review_df[col].astype(str).map(len).max(), len(col)) + 2
                rev_ws.set_column(i, i, max_len)

    output.seek(0)

    return send_file(output,
                     as_attachment=True,
                     download_name="selected_questions.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":

from flask import Flask, request, render_template_string, send_file
import sqlite3
import pandas as pd
import io
from datetime import datetime

app = Flask(__name__)

# HTML template with search, results, checkboxes, and export options
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Bible Quiz Search</title>
    <style>
        body { font-family: Arial; margin: 40px; background-color: #f9f9f9; }
        h1 { color: #333; }
        form { margin-bottom: 20px; }
        input[type="text"], select { padding: 8px; font-size: 14px; }
        input[type="submit"] { padding: 8px 16px; }
        .result { margin-bottom: 20px; padding: 10px; background: #fff; border: 1px solid #ccc; }
        .question { font-weight: bold; }
        .answer { color: green; }
    </style>
</head>
<body>
    <h1>🔍 Bible Quiz Search</h1>
    <form method="get">
        <input type="text" name="q" placeholder="Enter keyword..." value="{{ query }}">
        <select name="chapter">
            <option value="">-- All Chapters --</option>
            {% for ch in chapters %}
                <option value="{{ ch }}" {% if ch == selected_chapter %}selected{% endif %}>{{ ch }}</option>
            {% endfor %}
        </select>
        <input type="submit" value="Search">
    </form>

    {% if results %}
<form method="post" action="/export">
    <p><strong>{{ results|length }} result(s) found:</strong></p>

    <!-- Select All checkbox -->
    <label>
        <input type="checkbox" id="select-all"> Select All
    </label>
    <br><br>

    {% for row in results %}
        <div class="result">
            <input type="checkbox" name="selected_ids" value="{{ row[0] }}">
            <div class="question">Q: {{ row[2] }}</div>
            <div class="answer">✅ A: {{ row[3] }}</div>
            <ul>
                <li>B: {{ row[4] }}</li>
                <li>C: {{ row[5] }}</li>
                <li>D: {{ row[6] }}</li>
            </ul>
            <div><em>Chapter: {{ row[1] }}</em></div>
        </div>
    {% endfor %}

    <label>
        <input type="checkbox" name="remove_duplicates">
        Remove duplicates (based on Question text)
    </label><br><br>

    <input type="submit" value="Export Selected">
</form>

<!-- Script for Select All -->
<script>
document.getElementById("select-all").addEventListener("change", function(e) {
    const checked = e.target.checked;
    document.querySelectorAll('input[name="selected_ids"]').forEach(cb => {
        cb.checked = checked;
    });
});
</script>
{% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    query = request.args.get("q", "").strip()
    selected_chapter = request.args.get("chapter", "").strip()

    conn = sqlite3.connect("bible_quiz.db")
    cursor = conn.cursor()

    # Get distinct chapters for dropdown
    cursor.execute("SELECT DISTINCT chapter FROM questions ORDER BY chapter")
    chapters = [row[0] for row in cursor.fetchall()]

    # Build query dynamically
    sql = """
        SELECT id, chapter, correct_answer, question, answer_b, answer_c, answer_d
        FROM questions
        WHERE 1=1
    """
    params = []

    if query:
        sql += " AND (correct_answer LIKE ? OR question LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])

    if selected_chapter:
        sql += " AND chapter = ?"
        params.append(selected_chapter)

    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()

    return render_template_string(HTML_TEMPLATE,
                                  results=results,
                                  query=query,
                                  chapters=chapters,
                                  selected_chapter=selected_chapter)

@app.route("/export", methods=["POST"])
def export():
    selected_ids = request.form.getlist("selected_ids")

    if not selected_ids:
        return "⚠️ No questions selected."

    conn = sqlite3.connect("bible_quiz.db")
    cursor = conn.cursor()
    query = f"""
        SELECT chapter, correct_answer, question, answer_b, answer_c, answer_d
        FROM questions
        WHERE id IN ({','.join(['?']*len(selected_ids))})
    """
    cursor.execute(query, selected_ids)
    rows = cursor.fetchall()
    conn.close()

    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=["Chapter", "Question", "Correct Answer", "Answer B", "Answer C", "Answer D"])

    # Flag duplicates by Question text
    df["Is_Duplicate"] = df.duplicated(subset=["Question"], keep=False)

    # Group duplicates together
    df = df.sort_values(by=["Is_Duplicate", "Question"]).reset_index(drop=True)

    # Extract duplicates into a separate DataFrame
    duplicates_df = df[df["Is_Duplicate"] == True].copy()

    # Check if user wants to remove duplicates
    remove_dupes = request.form.get("remove_duplicates") == "on"
    if remove_dupes:
        df = df.drop_duplicates(subset=["Question"])

    # Prepare summary stats with timestamp
    summary_data = {
        "Export Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Total Selected": [len(rows)],
        "Unique Questions": [df["Question"].nunique()],
        "Duplicate Count": [len(duplicates_df)],
        "Duplicates Removed": ["Yes" if remove_dupes else "No"]
    }
    summary_df = pd.DataFrame(summary_data)

    # Build Duplicate Review dashboard
    review_df = (
        df.groupby("Question")
          .agg(
              Count=("Question", "size"),
              Chapters=("Chapter", lambda x: ", ".join(sorted(set(x))))
          )
          .reset_index()
    )
    review_df = review_df[review_df["Count"] > 1]

    # Write to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        red_fill = workbook.add_format({"bg_color": "#FFC7CE"})

        # --- Main sheet ---
        df.to_excel(writer, index=False, sheet_name="Selected Questions")
        ws = writer.sheets["Selected Questions"]
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(df), len(df.columns)-1)
        last_row = len(df) + 1
        ws.conditional_format(f"B2:B{last_row}", {"type": "duplicate", "format": red_fill})
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            ws.set_column(i, i, max_len)

        # --- Duplicates-only sheet ---
        if not duplicates_df.empty:
            duplicates_df.to_excel(writer, index=False, sheet_name="Duplicates Only")
            dup_ws = writer.sheets["Duplicates Only"]
            dup_ws.freeze_panes(1, 0)
            dup_ws.autofilter(0, 0, len(duplicates_df), len(duplicates_df.columns)-1)
            dup_last_row = len(duplicates_df) + 1
            dup_ws.conditional_format(f"A2:F{dup_last_row}", {"type": "no_blanks", "format": red_fill})
            for i, col in enumerate(duplicates_df.columns):
                max_len = max(duplicates_df[col].astype(str).map(len).max(), len(col)) + 2
                dup_ws.set_column(i, i, max_len)

        # --- Summary sheet ---
        summary_df.to_excel(writer, index=False, sheet_name="Export Summary")
        sum_ws = writer.sheets["Export Summary"]
        sum_ws.freeze_panes(1, 0)
        sum_ws.autofilter(0, 0, len(summary_df), len(summary_df.columns)-1)
        for i, col in enumerate(summary_df.columns):
            max_len = max(summary_df[col].astype(str).map(len).max(), len(col)) + 2
            sum_ws.set_column(i, i, max_len)

        # --- Duplicate Review sheet ---
        if not review_df.empty:
            review_df.to_excel(writer, index=False, sheet_name="Duplicate Review")
            rev_ws = writer.sheets["Duplicate Review"]
            rev_ws.freeze_panes(1, 0)
            rev_ws.autofilter(0, 0, len(review_df), len(review_df.columns)-1)
            rev_last_row = len(review_df) + 1
            rev_ws.conditional_format(f"B2:B{rev_last_row}", {
                "type": "cell",
                "criteria": ">",
                "value": 1,
                "format": red_fill
            })
            for i, col in enumerate(review_df.columns):
                max_len = max(review_df[col].astype(str).map(len).max(), len(col)) + 2
                rev_ws.set_column(i, i, max_len)

    output.seek(0)

    return send_file(output,
                     as_attachment=True,
                     download_name="selected_questions.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)