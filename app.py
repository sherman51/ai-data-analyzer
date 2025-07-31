st.title("📦 Master Pick Ticket Generator – Pick by Cart")

# Show chatbot in main content area
user_query = st.text_input("💬 Ask a question or request reprocessing:")

if user_query:
    response = chatbot(user_query, final_df)
    st.write(f"🤖 Chatbot: {response}")

# Add download button below
output = BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    final_df.to_excel(writer, index=False, sheet_name='Master Pick Ticket')
output.seek(0)

st.download_button(
    label="⬇️ Download Master Pick Ticket Excel",
    data=output,
    file_name="MasterPickTicket.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
