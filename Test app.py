import streamlit as st
import pandas as pd
import io
import os
from pathlib import Path

st.title("📂 Merge Excel Files from Folder (By Sheet Name)")

folder_path = st.text_input("Enter folder path containing Excel files:")

if folder_path:
    folder = Path(folder_path)

    if not folder.exists() or not folder.is_dir():
        st.error("❌ Invalid folder path.")
    else:
        excel_files = list(folder.glob("*.xlsx"))

        if not excel_files:
            st.warning("⚠️ No Excel files found in the folder.")
        else:
            st.write(f"🔍 Found {len(excel_files)} Excel files. Processing...")

            # Dictionary to hold all sheet data
            merged_sheets = {}

            for file in excel_files:
                xls = pd.read_excel(file, sheet_name=None)
                for sheet_name, df in xls.items():
                    if sheet_name in merged_sheets:
                        merged_sheets[sheet_name].append(df)
                    else:
                        merged_sheets[sheet_name] = [df]

            # Merge and write to in-memory file
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                for sheet_name, df_list in merged_sheets.items():
                    combined_df = pd.concat(df_list, ignore_index=True)
                    combined_df.to_excel(writer, sheet_name=sheet_name, index=False)
                writer.save()

            st.success("✅ Merging complete!")
            st.download_button(
                label="📥 Download Merged Excel File",
                data=output.getvalue(),
                file_name="merged_sheets.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
