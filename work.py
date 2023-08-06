import datetime
import streamlit as st
import requests
import json
import time

def createDbElement(token: str, databaseId: str, enum: str, work_date: str, detailed_work_time: str, worked_time: str, work_type: str) -> str:
    updateData = {
        "parent": {
            "database_id": databaseId
        },
        "properties": {
            "Name": {
                "title": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"Eintrag {enum}"
                        }
                    }
                ]
            },
            "Date": {    
                "date": {
                "start": work_date
                }
            },
             "Type": {
                "select": {
                    "name": work_type
                }
            },
            "Time": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": detailed_work_time
                        }
                    }
                ]
            },
            "Worked Time": {
                "type": "number",
                "number": worked_time
            }
        }
    }
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": "Bearer " + token,
        "accept": "application/json",
        "Notion-Version": "2022-06-28",
        "content-type": "application/json"
    }

    response = requests.post(url, json=updateData, headers=headers)

    return json.loads(response.text)


def readNotionDb(token, databaseId) -> dict:
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    readUrl = f"https://api.notion.com/v1/databases/{databaseId}/query"
    res = requests.post(readUrl, headers=headers)
    data = res.json()

    return data

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["streamlit_sec"]["streamlit_sec"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

#-------------------------------------------------------------------------------------------------
# Read credentials and init variables
notion_token = st.secrets['notion_db']["notion_token"]
notion_db_id = st.secrets['notion_db']["notion_db_id"]
table_content = readNotionDb(notion_token, notion_db_id)
sum_za = 0
break_day = False
work_type = 'NA'
#-------------------------------------------------------------------------------------------------
# Get ZA sum from Notion Db and create UI
for entry in table_content['results']:
    sum_za += entry['properties']['ZA']['formula']['number']

# create UI
st.title('Work Time Tracker')
if check_password():
    st.subheader(f'Current ZA Amount: {sum_za} hours')
    st.divider()
    sel_date = st.date_input('Date')
    #-------------------------------------------------------------------------------------------------
    # Speical Occasion section of UI
    st.subheader('Tick Box if Special Occasion')
    col1, col2, col3 = st.columns(3)
    za_day = col1.checkbox('Time Compensation')
    sick_leave = col2.checkbox('Sick Leave')
    vacation_day = col3.checkbox('Vacation')
    disable_time = za_day or sick_leave or vacation_day
    #-------------------------------------------------------------------------------------------------
    # Work Location section of UI
    st.divider()
    st.subheader('Tick Correct Work Location')
    col1, col2 = st.columns(2)
    ho_work = col1.checkbox('Home Office', disabled=disable_time)
    o_work = col2.checkbox('Office', disabled=disable_time)
    #-------------------------------------------------------------------------------------------------
    # Work Time section of UI
    st.divider()
    start_time = st.time_input('Start time', step=300, value=datetime.time(8, 0), disabled=disable_time)
    end_time = st.time_input('End time', step=300, value=datetime.time(16, 45), disabled=disable_time)
    st.divider()
    break_day = st.checkbox('Made a break?', disabled=disable_time)
    if break_day:
        break_start = st.time_input('Break start', step=300, value=datetime.time(12, 0), disabled=disable_time)
        break_end = st.time_input('Break end', step=300, value=datetime.time(12, 45), disabled=disable_time)
    st.divider()
    #-------------------------------------------------------------------------------------------------
    # Calculate worked time and create detailed worked time string
    if not disable_time:
        if break_day:
            detailed_worked_time = f'{start_time.strftime("%H:%M")} - {break_start.strftime("%H:%M")} | {break_end.strftime("%H:%M")} - {end_time.strftime("%H:%M")}'
            worked_time = (datetime.datetime.combine(datetime.date.today(), break_start) -
                        datetime.datetime.combine(datetime.date.today(), start_time)) + \
                        (datetime.datetime.combine(datetime.date.today(), end_time) -
                        datetime.datetime.combine(datetime.date.today(), break_end))
        else:
            detailed_worked_time = f'{start_time.strftime("%H:%M")} - {end_time.strftime("%H:%M")}'
            worked_time = datetime.datetime.combine(datetime.date.today(), end_time) - datetime.datetime.combine(datetime.date.today(), start_time)             
    else:
        detailed_worked_time = ' '

    #-------------------------------------------------------------------------------------------------
    # Prepare data for Notion Db upload
    if not disable_time:
        st.write(f'Worked Time: {worked_time}')
    if st.button('Submit to Notion'):
        if za_day:
            worked_time = datetime.date.today() - datetime.date.today()
            work_type = 'ZA'
        elif sick_leave or vacation_day:
            worked_time = datetime.time(4, 0)
            if sick_leave:
                work_type = 'SL'
            elif vacation_day:
                work_type = 'TU'
        else:
            if ho_work:
                work_type = 'HO'

        ret = createDbElement(token=notion_token, 
                        databaseId=notion_db_id, 
                        enum=str(len(table_content['results']) + 1), 
                        work_date=str(sel_date), 
                        detailed_work_time=detailed_worked_time,
                        worked_time=round(worked_time.seconds / 3600, 2),
                        work_type=work_type)
        if ret['object'] == 'page':
            st.caption(f'Notion Entry created: {ret["url"]}')
        