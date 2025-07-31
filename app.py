import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import smtplib
from email.mime.text import MIMEText
import openai

st.title("AI Data Analyzer + Automated Email Reporter")

# Upload CSV or Excel
uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.type == "text/csv":
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write("### Data Preview")
    st.dataframe(df.head())

    st.write("### Data Summary")
    st.write(df.describe())

    # Plot correlation heatmap for numeric data
    numeric_df = df.select_dtypes(include='number')
    if not numeric_df.empty:
        st.write("### Correlation Heatmap")
        fig, ax = plt.subplots()
        sns.heatmap(numeric_df.corr(), annot=True, ax=ax)
        st.pyplot(fig)
    else:
        st.write("No numeric columns to show correlation.")

    # OpenAI GPT summary
    st.write("### GPT Summary of Data")
    openai_api_key = st.text_input("Enter your OpenAI API key", type="password")
    if openai_api_key:
        openai.api_key = openai_api_key

        desc = df.describe().to_string()
        prompt = f"Summarize the following data description for a business user:\n{desc}"

        if st.button("Generate Summary"):
            with st.spinner("Generating summary..."):
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a helpful data analyst."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=200,
                        temperature=0.5,
                    )
                    summary = response['choices'][0]['message']['content']
                    st.write(summary)

                    # Save summary for email
                    st.session_state['summary'] = summary
                except Exception as e:
                    st.error(f"Error: {e}")

    # Download report button
    if uploaded_file and 'summary' in st.session_state:
        report_text = f"Data Summary Report\n\n{df.describe().to_string()}\n\nGPT Summary:\n{st.session_state['summary']}"

        report_bytes = report_text.encode('utf-8')
        st.download_button("Download Report as TXT", data=report_bytes, file_name="report.txt")

        # Email form
        st.write("### Send Report by Email")
        with st.form("email_form"):
            sender_email = st.text_input("Your Email (sender)")
            sender_password = st.text_input("Your Email Password or App Password", type="password")
            recipient_email = st.text_input("Recipient Email")
            submitted = st.form_submit_button("Send Email")

            if submitted:
                if sender_email and sender_password and recipient_email:
                    try:
                        msg = MIMEText(report_text)
                        msg['Subject'] = "Automated Data Analysis Report"
                        msg['From'] = sender_email
                        msg['To'] = recipient_email

                        server = smtplib.SMTP("smtp.gmail.com", 587)
                        server.starttls()
                        server.login(sender_email, sender_password)
                        server.send_message(msg)
                        server.quit()

                        st.success("Email sent successfully!")
                    except Exception as e:
                        st.error(f"Failed to send email: {e}")
                else:
                    st.error("Please fill in all email fields.")
