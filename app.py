import streamlit as st
import pandas as pd
import re
import io

def fn_for_streamlit(codechef_df, members_df, feedback_df, handles_df, no):
    # This function relies on exact column names from the dataframes passed to it.

    data = codechef_df.copy()
    data1 = members_df.copy()
    data2 = feedback_df.copy()
    handles = handles_df.copy()
    
    # --- Check 1: CodeChef Data columns ---
    # Requires 'Roll No' and 'Batch'
    if 'Roll No' not in data.columns:
        raise KeyError("Roll No")
        
    data.replace("Not Participated", 0, inplace=True)
    data['Roll No'] = data['Roll No'].astype(str).str.lower()

    # Starter columns check
    starter_cols = [col for col in data.columns if re.findall(r'Starters\s*\d+', col)]
    if not starter_cols:
        # This will still work if all values are 0, but usually indicates missing columns
        st.warning("Could not find any 'Starters X' columns. 'solve' score may be incorrect if not all problems are included.")
        
    data['solve'] = data[starter_cols].sum(axis=1)

    cols_to_drop = [col for col in starter_cols + ['Batch'] if col in data.columns]
    data.drop(columns=cols_to_drop, inplace=True, errors='ignore')
    
    # --- Check 2: Members Data columns ---
    # Requires 'username'
    if 'username' not in data1.columns:
        raise KeyError("username")
        
    data1['Roll No'] = data1['username'].astype(str).str.split('-').str[0].str.lower()
    merged_df = pd.merge(data, data1, on='Roll No', how='inner')

    # Requires 'email' (from data1)
    if 'email' not in merged_df.columns:
        raise KeyError("email")
        
    final_df = merged_df[['email', 'Roll No', 'solve']]
    
    # --- Check 3: Feedback Data columns ---
    # Requires 'Roll Number'
    if 'Roll Number' not in data2.columns:
        raise KeyError("Roll Number")
        
    data2.rename(columns={'Roll Number': 'Roll No'}, inplace=True)
    data2['Roll No'] = data2['Roll No'].astype(str).str.lower()
    df = pd.merge(final_df, data2, on='Roll No', how='left')
    df.rename(columns={'Roll No': 'RollNumber'}, inplace=True)
    
    # --- Check 4: Handles Data columns ---
    # Requires 'roll_number'
    if 'roll_number' not in handles.columns:
        raise KeyError("roll_number")
        
    handles['RollNumber'] = handles['roll_number'].astype(str).str.lower()

    # 'CODECHEF' is optional in handles, but checked later
    handle_cols = ['RollNumber', 'CODECHEF'] if 'CODECHEF' in handles.columns else ['RollNumber']
    handles = handles[handle_cols]
    df = df.merge(handles, on='RollNumber', how='left')
    
    # Requires 'Reason' (from data2)
    if 'Reason' not in df.columns and 'Feedback' not in df.columns: # Check both original and renamed
         # This error might be due to a previous missing column, but if Reason is missing, report it
         if 'Reason' not in data2.columns:
             raise KeyError("Reason")
         
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
            transition: background-color 0.3s;
        }
        .stButton>button:hover {
             background-color: #1a5c8e; 
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
            transition: background-color 0.3s;
        }
        .stDownloadButton>button:hover {
            background-color: #1f8b4c;
        }
        .css-1d391kg p {
            font-size: 1.1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("CodeChef Sincerity Score Generator")
    st.subheader("Automate scoring and feedback for CodeChef Starter events.")
    st.header("1. Upload Data Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        members_file = st.file_uploader(
            "Upload Members Data (`.csv`)", 
            type=['csv'], 
            help="**Required:** 'username' (e.g., RollNo-Name) and 'email'."
        )
        feedback_file = st.file_uploader(
            "Upload Feedback Data (`.xlsx` or `.xls`)", 
            type=['xlsx', 'xls'], 
            help="**Required:** 'Roll Number' and 'Reason'."
        )

    with col2:
        codechef_file = st.file_uploader(
            "Upload CodeChef Results (`.xlsx` or `.xls`)", 
            type=['xlsx', 'xls'], 
            help="**Required:** 'Roll No', 'Batch', and 'StartersX' columns."
        )
        handles_file = st.file_uploader(
            "Upload Handles Data (`.xlsx` or `.xls`)", 
            type=['xlsx', 'xls'], 
            help="**Required:** 'roll_number'. Optional: 'CODECHEF'."
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
                
        except KeyError as e:
            # Specific error handling for missing columns
            missing_key = str(e).strip("'").strip('"')
            st.error(f"**CRITICAL COLUMN ERROR:** The application failed because it could not find the column named: `{missing_key}` in one of the uploaded files.")
            st.markdown(
                """
                **Action Required:**
                1.  Please check the file descriptions under "1. Upload Data Files".
                2.  Ensure that the column name `""" + missing_key + """` is present with **exact** matching capitalization and spacing in the relevant uploaded file.
                """
            )
        except Exception as e:
            st.error("An unexpected error occurred during data processing. Please check your file formats and column names.")
            st.exception(e)
            st.markdown(f"**Error Details:** `{str(e)}`")

if __name__ == '__main__':
    app()
