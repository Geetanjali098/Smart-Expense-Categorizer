import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import io
import os
import pyarrow as pa

# ---------------------------------------------------------
# 1. SETUP & CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="Smart Expense Categorizer", page_icon="💰")

# ---------------------------------------------------------
# 2. TRAINING DATA (The "Indian Context")
# ---------------------------------------------------------
# In a real app, you would load this from a CSV of your past transactions.
# I've created a robust starter set for the Indian context.
training_data = [
    # Food
    ("Swiggy order", "Food"),
    ("Zomato", "Food"),
    ("Dominos", "Food"),
    ("McDonalds", "Food"),
    ("Restaurant", "Food"),
    ("Dinner", "Food"),
    ("Lunch", "Food"),
    
    # Shopping
    ("Amazon", "Shopping"),
    ("Flipkart", "Shopping"),
    ("Myntra", "Shopping"),
    ("Ajio", "Shopping"),
    ("Cloth", "Shopping"),
    ("Shoe", "Shopping"),
    ("Meesho", "Shopping"),
    
    
    # Transport
    ("Uber", "Transport"),
    ("Ola", "Transport"),
    ("Petrol", "Transport"),
    ("Fuel", "Transport"),
    ("Metro", "Transport"),
    ("Bus ticket", "Transport"),
    ("Train ticket", "Transport"),
    
    # Bills & Utilities
    ("Electricity bill", "Bills"),
    ("Wifi", "Bills"),
    ("Mobile recharge", "Bills"),
    ("DTH", "Bills"),
    ("Gas bill", "Bills"),
    ("Water bill", "Bills"),
    
    # Personal & Transfer
    ("UPI transfer", "Personal"),
    ("Paid to Ramesh", "Personal"),
    ("Google Pay", "Personal"),
    ("PhonePe", "Personal"),
    ("IMPS", "Transfer"),
    ("NEFT", "Transfer"),
    ("Cash withdrawal", "Personal"),
    
    # Income
    ("Salary", "Income"),
    ("Interest", "Income"),
    ("Credit", "Income"),
    ("Refund", "Income")
]

# Extract features and labels
X_train = [item[0] for item in training_data]
y_train = [item[1] for item in training_data]

# ---------------------------------------------------------
# 3. MODEL TRAINING
# ---------------------------------------------------------
# We use TF-IDF (Term Frequency-Inverse Document Frequency) to convert 
# text into numbers, then Naive Bayes to classify.
def train_model():
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer()),
        ('classifier', MultinomialNB())
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

# Train immediately upon script run
model = train_model()

# ---------------------------------------------------------
# 4. STREAMLIT UI
# ---------------------------------------------------------
st.title("💰 Smart Expense Categorizer (India)")
st.markdown("""
Upload your bank statement CSV. The AI will read the **Description/Narration** 
and automatically categorize your expenses.
""")

# Step 1: File Upload
uploaded_file = st.file_uploader(
    "Upload your Bank Statement (CSV or Excel)",
    type=['csv', 'xlsx']
)

if uploaded_file is not None:
    try:
        file_extension = os.path.splitext(uploaded_file.name)[1]

 # Read file based on extension
        if file_extension == ".csv":
            try:
                df = pd.read_csv(uploaded_file)
            except UnicodeDecodeError:
                df = pd.read_csv(uploaded_file, encoding="latin1")

        elif file_extension == ".xlsx":
            df = pd.read_excel(uploaded_file)

        else:
            st.error("Unsupported file format!")
            st.stop()

        # --------------------------------------------------
        # convert any unusual or complex objects to simple
        # types before handing the dataframe back to Streamlit
        # Arrow serialization errors often come from columns
        # containing lists/dicts/mixed types; casting to str
        # or using pandas' convert_dtypes helps avoid that.
        def make_arrow_compatible(frame: pd.DataFrame) -> pd.DataFrame:
            # try a dtype conversion first
            frame = frame.convert_dtypes()
            # fall back to string for anything that still won't
            # serialize (object columns with unhashable values)
            for c in frame.columns:
                if frame[c].dtype == "object":
                    try:
                        # attempt to create arrow array
                        _ = pa.array(frame[c])
                    except Exception:
                        frame[c] = frame[c].astype(str)
            return frame

        df = make_arrow_compatible(df)

        # ----------------------------
        # Data Preview
        # ----------------------------
        st.subheader("📄 Data Preview")
        st.dataframe(df.head())

        st.subheader("⚙️ Configuration")

        columns = df.columns.tolist()

        desc_col = st.selectbox(
            "Select the Description/Narration column",
            options=columns
        )
        
        amount_col = st.selectbox(
            "Select the Amount column (optional, for analytics)",
            options=["None"] + columns
        )
        
          # Safety check
        if desc_col not in df.columns:
            st.error("Selected column not found.")
            st.stop()

        # ----------------------------
        # Categorization
        # ----------------------------

        if st.button("Categorize Expenses"):

            with st.spinner("AI is thinking..."):

                df_clean = df.dropna(subset=[desc_col]).copy()
                
                predictions = model.predict(df_clean[desc_col].astype(str))

                df_clean["Predicted Category"] = predictions

         # make sure we won't hit arrow serialization issues again
                df_clean = make_arrow_compatible(df_clean)

                st.success("Categorization Complete! 🎉")

                st.dataframe(df_clean)

          # ----------------------------
          # Analytics
          # ----------------------------
                if amount_col != "None" and amount_col in df_clean.columns:

                    st.markdown("### 📊 Spending Breakdown")

                    try:
                        df_clean[amount_col] = (
                            df_clean[amount_col]
                            .astype(str)
                            .str.replace("₹", "")
                            .str.replace(",", "")
                        )

                        df_clean[amount_col] = pd.to_numeric(
                            df_clean[amount_col], errors="coerce"
                        )

                        category_sum = (
                            df_clean.groupby("Predicted Category")[amount_col]
                            .sum()
                            .sort_values(ascending=False)
                        )

                        st.bar_chart(category_sum)

                    except:
                        st.warning("Could not parse Amount column.")
                        st.write(df_clean["Predicted Category"].value_counts())

            # ----------------------------
            # Download Button
            # ----------------------------
                csv_buffer = io.StringIO()
                df_clean.to_csv(csv_buffer, index=False)

                st.download_button(
                    label="Download Categorized CSV",
                    data=csv_buffer.getvalue(),
                    file_name="categorized_expenses.csv",
                    mime="text/csv"
                )

    except Exception as e:
        st.error(f"Error processing file: {e}")

else:
    st.info("Please upload a CSV or Excel file to begin.")

    st.markdown("---")
    st.markdown("### 📝 Sample CSV Format")

    sample_data = pd.DataFrame({
        'Date': ['2026-02-01', '2026-02-02', '2026-02-03'],
        'Description': ['Swiggy order', 'Uber trip', 'Salary credit'],
        'Amount': [-350, -150, 50000]
    })

    st.table(sample_data)