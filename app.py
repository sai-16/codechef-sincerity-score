import streamlit as st
import pandas as pd
import re
import io

def fn_for_streamlit(codechef_df, members_df, feedback_df, handles_df, no):
    data = codechef_df.copy()
    data1 = members_df.copy()
    data2 = feedback_df.copy()
    handles = handles_df.copy()
    data.replace("Not Participated", 0, inplace=True)
    data['Roll No'] = data['Roll No'].astype(str).str.lower()

    starter_cols = [col for col in data.columns if re.findall(r'Starters\s*\d+', col)]
    data['solve'] = data[starter_cols].sum(axis=1)

    cols_to_drop = [col for col in starter_cols + ['Batch'] if col in data.columns]
    data.drop(columns=cols_to_drop, inplace=True, errors='ignore')
    data1['Roll No'] = data1['username'].astype(str).str.split('-').str[0].str.lower()
    merged_df = pd.merge(data, data1, on='Roll No', how='inner')

    final_df = merged_df[['email', 'Roll No', 'solve']]
    data2.rename(columns={'Roll Number': 'Roll No'}, inplace=True)
    data2['Roll No'] = data2['Roll No'].astype(str).str.lower().str().rstrip()
    df = pd.merge(final_df, data2, on='Roll No', how='left')
    df.rename(columns={'Roll No': 'RollNumber'}, inplace=True)
    handles['RollNumber'] = handles['roll_number'].astype(str).str.lower()

    handle_cols = ['RollNumber', 'CODECHEF'] if 'CODECHEF' in handles.columns else ['RollNumber']
    handles = handles[handle_cols]
    df = df.merge(handles, on='RollNumber', how='left')
    df.rename(columns={'Reason': 'Feedback'}, inplace=True)
    codechef_handle_col = 'CODECHEF' if 'CODECHEF' in df.columns else None
    
    df['Feedback'] = df.apply(
        lambda row: f"CODECHEF-START{no} ATTENDED, SOLVED : {row['solve']} ({row.get('CODECHEF', 'N/A')})"
        if pd.isna(row.get('Feedback'))
        else f"CODECHEF-START{no} DID NOT PARTICIPATE, REASON - {row.get('Feedback')} ({row.get('CODECHEF', 'N/A')})",
        axis=1
    )
    df['solve'] = (df['solve'] >= 2).astype(int)
    
    df.rename(columns={'solve': 'Score', 'email': 'Email'}, inplace=True)
    df.set_index("Email", inplace=True)

    if codechef_handle_col and codechef_handle_col in df.columns:
        del df[codechef_handle_col]
    if 'Timestamp' in df.columns:
        del df['Timestamp']
    df['RollNumber'] = df['RollNumber'].astype(str).str.upper()
    
    return df

def app():
    st.set_page_config(
        page_title="CodeChef Report Generator",
        layout="centered",
    )

    st.markdown("""
    <style>
        /* Primary button for generation */
        .stButton>button {
            width: 100%;
            background-color: #2E86C1; /* A nice blue */
            color: white;
            font-weight: bold;
            border-radius: 8px;
            padding: 10px;
        }
        /* Download button styling */
        .stDownloadButton>button {
            width: 100%;
            background-color: #27AE60; /* A nice green */
            color: white;
            font-weight: bold;
            border-radius: 8px;
            padding: 10px;
            margin-top: 15px;
        }
        .css-1d391kg p {
            font-size: 1.1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("CodeChef Sincerity Score")
    st.header("1. Upload Data Files")
    col1, col2 = st.columns(2)
    
    with col1:
        members_file = st.file_uploader(
            "Upload Members Data (`.csv`)", 
            type=['csv'], 
            help="Contains 'username' (e.g., RollNo-Name) and 'email'."
        )
        feedback_file = st.file_uploader(
            "Upload Feedback Data (`.xlsx` or `.xls`)", 
            type=['xlsx', 'xls'], 
            help="Contains 'Roll Number' and 'Reason' (for non-participation)."
        )

    with col2:
        codechef_file = st.file_uploader(
            "Upload CodeChef Results (`.xlsx` or `.xls`)", 
            type=['xlsx', 'xls'], 
            help="Contains 'Roll No', 'Batch', and 'StartersX' columns (multiple problem columns)."
        )
        handles_file = st.file_uploader(
            "Upload Handles Data (`.xlsx` or `.xls`)", 
            type=['xlsx', 'xls'], 
            help="Contains 'roll_number' and 'CODECHEF' handle."
        )

    st.header("2. Specify Event Number")
    no = st.number_input(
        "Enter the CodeChef Starter Number:", 
        min_value=1, 
        value=85, 
        step=1, 
        key='no',
        help="This number is used in the report name and feedback message (e.g., CodeChef-Start85)."
    )

    st.header("3. Generate Report")
    
    all_files_uploaded = members_file and codechef_file and feedback_file and handles_file

    if st.button("Process Data and Generate Report", disabled=not all_files_uploaded):
        if not all_files_uploaded:
            st.error("Please ensure all four required files are uploaded.")
            return

        try:
            with st.spinner('Reading and processing data... This may take a moment.'):
                members_df = pd.read_csv(members_file)
                codechef_df = pd.read_excel(codechef_file, engine='openpyxl')
                feedback_df = pd.read_excel(feedback_file, engine='openpyxl') 
                handles_df = pd.read_excel(handles_file, engine='openpyxl')
                final_df = fn_for_streamlit(
                    codechef_df, members_df, feedback_df, handles_df, no
                )
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_df.to_excel(writer, index=True, sheet_name='Results')
                output.seek(0)
                
                filename = f'CodeChef_Report_{no}.xlsx'

                st.success("Processing complete! Your report is ready for download.")
                st.download_button(
                    label="Download Processed Report",
                    data=output,
                    file_name=filename,
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                st.subheader("Preview of the Final Data (First 10 Rows)")
                st.dataframe(final_df.head(10), use_container_width=True)
                
        except Exception as e:
            st.error("An unexpected error occurred during data processing. Please check your file formats and column names.")
            st.exception(e)
            st.markdown(f"**Error Details:** `{str(e)}`")

if __name__ == '__main__':
    app()


