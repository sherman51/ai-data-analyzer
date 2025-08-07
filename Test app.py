import streamlit as st
import pandas as pd
import io

st.title("🧾 Merge Excel Files by Sheet Name")

uploaded_files = st.file_uploader(
    "Upload Excel files", type=["xlsx"], accept_multiple_files=True
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} file(s) uploaded. Click the button below to merge.")
    
    if st.button("🔀 Merge Files"):
        merged_sheets = {}

        for uploaded_file in uploaded_files:
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

        # Create merged Excel in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output) as writer:
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

