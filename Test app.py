import streamlit as st
import pandas as pd
import io

st.title("🧾 Merge Excel Files by Sheet Name")

st.write("Upload multiple Excel files. Sheets with the same name will be merged into one.")

# Upload multiple Excel files
uploaded_files = st.file_uploader(
    "Upload Excel files", type=["xlsx"], accept_multiple_files=True
)

if uploaded_files:
    merged_sheets = {}

    for uploaded_file in uploaded_files:
        # Read all sheets from current file
        try:
            xls = pd.read_excel(uploaded_file, sheet_name=None)
        except Exception as e:
            st.error(f"Failed to read {uploaded_file.name}: {e}")
            continue

        for sheet_name, df in xls.items():
            if sheet_name in merged_sheets:
                merged_sheets[sheet_name].append(df)
            else:
                merged_sheets[sheet_name] = [df]

    # Merge and write to output Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for sheet_name, df_list in merged_sheets.items():
            merged_df = pd.concat(df_list, ignore_index=True)
            merged_df.to_excel(writer, sheet_name=sheet_name, index=False)
        writer.save()

    st.success("✅ Files merged successfully!")
    st.download_button(
        label="📥 Download Merged Excel File",
        data=output.getvalue(),
        file_name="merged_sheets.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
