from flask import Flask, render_template, request, send_file
import pandas as pd
import re
import os
import uuid

app = Flask(__name__)

def fn(data, data1, data2, no, handles):
    data.replace("Not Participated", 0, inplace=True)
    data['Roll No'] = data['Roll No'].str.lower()
    starters_cols = [c for c in data.columns if re.findall(r'Starters\s*\d+', c)]
    data['solve'] = data[starters_cols].sum(axis=1)
    data.drop(columns=starters_cols + ['Batch'], inplace=True)
    data1['Roll No'] = data1['username'].str.split('-').str[0].str.lower()
    merged_df = pd.merge(data, data1, on='Roll No', how='inner')
    final_df = merged_df[['email', 'Roll No', 'solve']]
    data2.rename(columns={'Roll Number': 'Roll No'}, inplace=True)
    data2['Roll No'] = data2['Roll No'].str.lower()
    df = pd.merge(final_df, data2, on='Roll No', how='left')
    df.rename(columns={'Roll No': 'RollNumber'}, inplace=True)
    handles['RollNumber'] = handles['roll_number'].str.lower()
    handles = handles[['RollNumber','CODECHEF']]
    df = df.merge(handles, on='RollNumber', how='left')
    df.rename(columns={'Reason': 'Feedback'}, inplace=True)
    df['Feedback'] = df.apply(
        lambda row: f"CODECHEF-START{no} ATTENDED, SOLVED : {row['solve']} - ({row['CODECHEF']})"
        if pd.isna(row['Feedback'])
        else f"CODECHEF-START{no} DID NOT PARTICIPATE, REASON - {row['Feedback']} - ({row['CODECHEF']})",
        axis=1
    )
    df['solve'] = (df['solve'] >= 2).astype(int)
    df.rename(columns={'solve': 'Score', 'email': 'Email'}, inplace=True)
    df.set_index("Email", inplace=True)
    del df['CODECHEF']
    if 'Timestamp' in df.columns:
        del df['Timestamp']
    df['RollNumber'] = df['RollNumber'].str.upper()
    return df

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        members = request.files['members']
        codechef = request.files['codechef']
        feedback = request.files['feedback']
        handles = request.files['handles']
        no = request.form['no']

        data1 = pd.read_csv(members)
        data = pd.read_excel(codechef, engine='openpyxl')
        data2 = pd.read_excel(feedback)
        handles_df = pd.read_excel(handles, engine='openpyxl')

        df = fn(data, data1, data2, no, handles_df)

        unique_id = uuid.uuid4().hex[:8]
        output_path = f'static/output_start{no}_{unique_id}.xlsx'
        df.to_excel(output_path)

        return render_template('index.html', download_link=output_path, contest_no=no)

    return render_template('index.html', download_link=None)

@app.route('/download/<path:filename>')
def download(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

