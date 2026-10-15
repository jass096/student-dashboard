
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
from dotenv import load_dotenv

# -----------------------------
# 1. Page configuration
# -----------------------------
st.set_page_config(
    page_title="Student Performance Dashboard",
    page_icon="🎓",
    layout="wide"
)

load_dotenv()

st.title("🎓 Student Academic Performance Dashboard")
st.write("Analyse student marks, attendance, and academic performance.")

# -----------------------------
# 2. Connect to MongoDB Atlas
# -----------------------------
@st.cache_resource
def get_collection():
    mongo_uri = os.getenv("MONGO_URI")

    if not mongo_uri:
        raise ValueError("MONGO_URI is missing from the .env file.")

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")

    # Uses the database and collection specified in the URI below.
    # Change StudentsDB if your database has another name.
    db = client["Students"]
    return db["Students"]

try:
    collection = get_collection()
    records = list(collection.find({}, {"_id": 0}))

except Exception as e:
    st.error("Could not connect to MongoDB Atlas or read the collection.")
    st.code(str(e))
    st.info(
        "Check your .env connection string, database name, "
        "collection name, and Atlas Network Access settings."
    )
    st.stop()

# -----------------------------
# 3. Load and prepare data
# -----------------------------
if not records:
    st.warning(
        "No student records found. Insert your sample records "
        "into the Students collection first."
    )
    st.stop()

df = pd.DataFrame(records)

subjects = [
    "DBMS",
    "Python",
    "Mathematics",
    "Statistics",
    "Java"
]

required_columns = [
    "student_id", "name", "department",
    "attendance", "marks"
]

missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns:
    st.error(f"Missing required fields: {missing_columns}")
    st.stop()

# Extract nested marks into separate columns
for subject in subjects:
    df[subject] = df["marks"].apply(
        lambda m: m.get(subject) if isinstance(m, dict) else None
    )
    df[subject] = pd.to_numeric(df[subject], errors="coerce")

df["attendance"] = pd.to_numeric(
    df["attendance"], errors="coerce"
)

# Calculate average using available subject marks
df["Average Marks"] = df[subjects].mean(axis=1)

df["Performance"] = df["Average Marks"].apply(
    lambda x: (
        "Excellent" if x >= 85 else
        "Good" if x >= 70 else
        "Average" if x >= 50 else
        "Needs Improvement"
    ) if pd.notna(x) else "No Marks"
)

# -----------------------------
# 4. Sidebar filters
# -----------------------------
st.sidebar.header("🔎 Filter Students")

departments = sorted(
    df["department"].dropna().unique().tolist()
)

selected_departments = st.sidebar.multiselect(
    "Select Department",
    departments,
    default=departments
)

filtered_df = df[
    df["department"].isin(selected_departments)
].copy()

if filtered_df.empty:
    st.warning("No students match the selected filters.")
    st.stop()

# -----------------------------
# 5. Summary metrics
# -----------------------------
total_students = len(filtered_df)
average_marks = filtered_df["Average Marks"].mean()
average_attendance = filtered_df["attendance"].mean()

topper = filtered_df.loc[
    filtered_df["Average Marks"].idxmax()
]

needs_support = (
    filtered_df["Average Marks"] < 50
).sum()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Students", total_students)

col2.metric(
    "Class Average",
    f"{average_marks:.2f}/100"
    if pd.notna(average_marks) else "N/A"
)

col3.metric(
    "Average Attendance",
    f"{average_attendance:.1f}%"
    if pd.notna(average_attendance) else "N/A"
)

col4.metric("Need Academic Support", int(needs_support))

st.divider()

# -----------------------------
# 6. Topper information
# -----------------------------
st.subheader("🏆 Top Performer")

c1, c2, c3 = st.columns(3)

c1.write(f"**Name:** {topper['name']}")
c2.write(f"**Department:** {topper['department']}")
c3.write(f"**Average Marks:** {topper['Average Marks']:.2f}/100")

# -----------------------------
# 7. Subject-wise average chart
# -----------------------------
st.subheader("📊 Subject-wise Average Marks")

subject_averages = (
    filtered_df[subjects]
    .mean()
    .rename_axis("Subject")
    .reset_index(name="Average Marks")
)

fig_subject = px.bar(
    subject_averages,
    x="Subject",
    y="Average Marks",
    text_auto=".2f",
    color="Average Marks",
    range_y=[0, 100],
    title="Average Marks in Each Subject"
)

st.plotly_chart(fig_subject, use_container_width=True)

# -----------------------------
# 8. Individual student performance
# -----------------------------
st.subheader("📈 Student-wise Performance")

performance_data = filtered_df.melt(
    id_vars=["name", "department"],
    value_vars=subjects,
    var_name="Subject",
    value_name="Marks"
)

fig_students = px.bar(
    performance_data,
    x="name",
    y="Marks",
    color="Subject",
    barmode="group",
    range_y=[0, 100],
    title="Subject Marks by Student"
)

st.plotly_chart(fig_students, use_container_width=True)

# -----------------------------
# 9. Performance distribution
# -----------------------------
st.subheader("📌 Performance Distribution")

performance_counts = (
    filtered_df["Performance"]
    .value_counts()
    .rename_axis("Performance")
    .reset_index(name="Number of Students")
)

fig_pie = px.pie(
    performance_counts,
    names="Performance",
    values="Number of Students",
    hole=0.4,
    title="Students by Performance Category"
)

st.plotly_chart(fig_pie, use_container_width=True)

# -----------------------------
# 10. Attendance vs marks
# -----------------------------
st.subheader("📚 Attendance vs Academic Performance")

attendance_data = filtered_df.dropna(
    subset=["attendance", "Average Marks"]
)

fig_attendance = px.scatter(
    attendance_data,
    x="attendance",
    y="Average Marks",
    color="department",
    hover_name="name",
    range_x=[0, 100],
    range_y=[0, 100],
    title="Does Attendance Relate to Marks?"
)

st.plotly_chart(fig_attendance, use_container_width=True)

# -----------------------------
# 11. Student data table
# -----------------------------
st.subheader("📋 Student Records")

display_columns = [
    "student_id", "name", "department",
    "attendance", *subjects, "Average Marks", "Performance"
]

display_df = filtered_df[display_columns].copy()
display_df["Average Marks"] = display_df["Average Marks"].round(2)

st.dataframe(
    display_df.sort_values(
        "Average Marks", ascending=False, na_position="last"
    ),
    use_container_width=True,
    hide_index=True
)

# -----------------------------
# 12. Download report
# -----------------------------
csv_data = display_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Student Performance Report",
    data=csv_data,
    file_name="student_performance_report.csv",
    mime="text/csv"
)

st.success("Dashboard loaded successfully!")
