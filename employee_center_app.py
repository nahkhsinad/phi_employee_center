
'''
#LKWC

import streamlit as st
import pandas as pd
import sqlite3
import re
from datetime import datetime, date
import logging
import bcrypt
import requests
from io import BytesIO
from PIL import Image
from dateutil import parser

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set page configuration
st.set_page_config(page_title="Employee Centre", layout="wide")

# Apply custom CSS
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        logging.error(f"CSS file {file_name} not found.")
        st.error(f"CSS file {file_name} not found.")

local_css("assets/styles.css")

# Database connection
@st.cache_resource
def get_connection():
    try:
        conn = sqlite3.connect('database/employee_center.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection failed: {e}")
        st.error("Failed to connect to the database.")
        return None

# Load employee data
@st.cache_data
def load_employee_data():
    conn = get_connection()
    if conn:
        try:
            df = pd.read_sql_query("SELECT * FROM employee_center", conn)
            df['Employee UID# (EUID#)'] = pd.to_numeric(df['Employee UID# (EUID#)'], errors='coerce').astype('Int64')
            string_cols = df.select_dtypes(['object']).columns
            df[string_cols] = df[string_cols].apply(lambda x: x.str.strip())
            return df
        except sqlite3.Error as e:
            logging.error(f"Failed to load employee data: {e}")
            st.error("Failed to load employee data.")
            return pd.DataFrame()
    else:
        return pd.DataFrame()

# Helper function to clean and convert salary strings to float
def clean_salary(salary_str):
    if isinstance(salary_str, str):
        cleaned_str = re.sub(r'[^\d.]', '', salary_str)
        return float(cleaned_str) if cleaned_str else 0.0
    elif isinstance(salary_str, (int, float)):
        return salary_str
    else:
        return 0.0

# User Authentication
def authenticate(username, pin):
    df = load_employee_data()
    if df.empty:
        logging.warning("Employee data is empty. Authentication failed.")
        return False
    user = df[df['Employee UID# (EUID#)'] == username]
    if not user.empty:
        stored_pin = user.iloc[0]['PIN']
        if stored_pin:
            if stored_pin.startswith('$2b$') or stored_pin.startswith('$2a$'):
                try:
                    return bcrypt.checkpw(pin.encode('utf-8'), stored_pin.encode('utf-8'))
                except ValueError as ve:
                    logging.error(f"Bcrypt error: {ve}")
                    return False
            else:
                return pin == stored_pin
    return False

# Main Application
def main():
    st.sidebar.title("Employee Centre")
    logging.info("Application started")

    # Initialize session state
    if 'auth_status' not in st.session_state:
        st.session_state.auth_status = False
        st.session_state.username = None

    # User Authentication
    if not st.session_state.auth_status:
        st.sidebar.subheader("Login")
        employee_uids = load_employee_data()['Employee UID# (EUID#)'].dropna().unique().tolist()
        if employee_uids:
            username = st.sidebar.selectbox("Select EUID#", options=employee_uids)
        else:
            username = st.sidebar.text_input("Enter EUID#")
        pin = st.sidebar.text_input("Enter PIN", type="password")
        if st.sidebar.button("Login"):
            if authenticate(username, pin):
                st.session_state.auth_status = True
                st.session_state.username = username
                st.success("Logged in successfully.")
                st.rerun()
            else:
                st.sidebar.error("Invalid credentials")
    else:
        st.sidebar.success(f"Logged in as EUID# {st.session_state.username}")
        if st.sidebar.button("Logout"):
            st.session_state.auth_status = False
            st.session_state.username = None
            st.rerun()

    # Main Application Logic
    if st.session_state.auth_status:
        display_dashboard()

# Dashboard
def display_dashboard():
    st.title("Employee Centre Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.image("https://pic.onlinewebfonts.com/thumbnails/icons_331521.svg", width=200)
        if st.button("View Profile"):
            st.session_state.current_page = "view_profile"
            st.rerun()

    with col2:
        st.image("https://pic.onlinewebfonts.com/thumbnails/icons_568816.svg", width=200)
        if st.button("Edit Profile"):
            st.session_state.current_page = "edit_profile"
            st.rerun()

    with col3:
        st.image("https://pic.onlinewebfonts.com/thumbnails/icons_523333.svg", width=200)
        if st.button("More phi_apps"):
            st.session_state.current_page = "more_apps"
            st.rerun()

    if 'current_page' in st.session_state:
        if st.session_state.current_page == "view_profile":
            view_employee_profile()
        elif st.session_state.current_page == "edit_profile":
            edit_employee_profile()
        elif st.session_state.current_page == "more_apps":
            display_more_apps()

# View Employee Profile
def view_employee_profile():
    st.title("View Profile")
    logging.info("Viewing employee profile")

    df = load_employee_data()
    if df.empty:
        st.error("No employee data available.")
        return

    # Fetch data for the logged-in employee
    username = st.session_state.username
    employee_data = df[df['Employee UID# (EUID#)'] == username]

    if not employee_data.empty:
        employee_data = employee_data.iloc[0]
        st.subheader(f"Employee UID#: {employee_data['Employee UID# (EUID#)']}")
        st.subheader(f"Employee Name: {employee_data['Employee Full Name']}")

        # Display Profile Picture
        photograph_url = employee_data.get('Photograph', None)
        if photograph_url:
            try:
                response = requests.get(photograph_url)
                img = Image.open(BytesIO(response.content))
                st.image(img, width=150, caption="Profile Picture")
            except Exception as e:
                logging.error(f"Failed to load profile picture: {e}")
                st.warning("Profile picture not available.")
        else:
            st.info("No profile picture provided.")

        # Display Sections in Tabs
        tabs = st.tabs([
            "General Details",
            "Definitives",
            "Personal Details",
            "Payroll",
            "Salary Breakup",
            "Career Progression",
            "Performance Reviews"
        ])

        with tabs[0]:
            st.header("General Details")
            display_section(employee_data, 'SECTION- GENERAL DETAILS', 'SECTION- DEFINITIVES', editable=False)

        with tabs[1]:
            st.header("Definitives")
            display_section(employee_data, 'SECTION- DEFINITIVES', 'SECTION- PERSONAL DETAILS', editable=False)

        with tabs[2]:
            st.header("Personal Details")
            display_section(employee_data, 'SECTION- PERSONAL DETAILS', 'SECTION- PAYROLL', editable=False)

        with tabs[3]:
            st.header("Payroll")
            display_section(employee_data, 'SECTION- PAYROLL', 'SECTION- SALARY BREAK UP', editable=False)

        with tabs[4]:
            st.header("Salary Breakup")
            display_salary_breakup(employee_data)

        with tabs[5]:
            st.header("Career Progression")
            display_section(employee_data, 'SECTION- LCT', 'SECTION- PR', editable=False)

        with tabs[6]:
            st.header("Performance Reviews")
            display_performance_reviews(employee_data, 'SECTION- PR', None)
    else:
        st.error("Employee data not found.")


# Edit Employee Profile
def edit_employee_profile():
    st.title("Edit Profile")
    logging.info("Editing employee profile")

    df = load_employee_data()
    if df.empty:
        st.error("No employee data available.")
        return

    # Fetch data for the logged-in employee
    username = st.session_state.username
    employee_data = df[df['Employee UID# (EUID#)'] == username]

    if not employee_data.empty:
        employee_data = employee_data.iloc[0].to_dict()
        
        # Define all sections
        sections = [
            ('General Details', 'SECTION- GENERAL DETAILS', 'SECTION- DEFINITIVES', True),
            ('Definitives', 'SECTION- DEFINITIVES', 'SECTION- PERSONAL DETAILS', True),
            ('Personal Details', 'SECTION- PERSONAL DETAILS', 'SECTION- PAYROLL', True),
            ('Payroll', 'SECTION- PAYROLL', 'SECTION- SALARY BREAK UP', False),
            ('Salary Breakup', 'SECTION- SALARY BREAK UP', 'SECTION- LCT', False),
            ('Career Progression', 'SECTION- LCT', 'SECTION- PR', False),
            ('Performance Reviews', 'SECTION- PR', None, False)
        ]

        # Create a single set of tabs for all sections
        tabs = st.tabs([section[0] for section in sections])

        with st.form("edit_employee_form"):
            updated_data = {}
            for i, (section_name, start_col, end_col, is_editable) in enumerate(sections):
                with tabs[i]:
                    st.subheader(section_name)
                    if is_editable:
                        # Editable Sections
                        section_data = collect_section_input(start_col, end_col, employee_data)
                        updated_data.update(section_data)
                    else:
                        # Non-Editable Sections (Read-Only Display)
                        display_section(employee_data, start_col, end_col, editable=False)

            submit_button = st.form_submit_button("Save Changes")
            if submit_button:
                if updated_data:
                    if save_employee_changes(username, updated_data):
                        st.success("Your profile has been updated successfully!")
                    else:
                        st.error("Failed to update your profile.")
                else:
                    st.info("No changes to save.")
    else:
        st.error("Employee data not found.")


# Parse Date
def parse_date(date_string):
    if not date_string:
        return None
    try:
        # Try parsing with dateutil
        return parser.parse(date_string).date()
    except (ValueError, TypeError):
        try:
            # Try parsing with a specific format
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except ValueError:
            # If all parsing attempts fail, return None
            return None

# Collect Section Input
def collect_section_input(start_col, end_col, existing_data):
    conn = get_connection()
    section_data = {}
    if conn:
        try:
            df_columns = pd.read_sql_query('PRAGMA table_info(employee_center)', conn)
            columns = df_columns['name'].tolist()

            start_idx = columns.index(start_col) + 1 if start_col in columns else 0
            end_idx = columns.index(end_col) if end_col in columns else len(columns)
            section_columns = columns[start_idx:end_idx]

            for col in section_columns:
                existing_value = existing_data.get(col, '')
                
                if col == 'DIVISION':
                    existing_options = pd.read_sql_query('SELECT DISTINCT "DIVISION" FROM employee_center', conn)['DIVISION'].dropna().tolist()
                    if 'Philocaly Spaces Pvt. Ltd.' not in existing_options:
                        existing_options.insert(0, 'Philocaly Spaces Pvt. Ltd.')
                    selected_value = st.selectbox(col, options=existing_options, key=f'division_{col}', index=(existing_options.index(existing_value) if existing_value in existing_options else 0))
                    new_value = st.text_input('Add new DIVISION (leave blank if not adding new)', key=f'new_division_{col}')
                    if new_value:
                        selected_value = new_value
                    section_data[col] = selected_value
                elif col in ['Date of Joining', 'DOB']:
                    parsed_date = parse_date(str(existing_value))
                    default_date = parsed_date if parsed_date else date.today()
                    date_value = st.date_input(col, default_date, key=f'date_{col}')
                    section_data[col] = date_value.strftime('%Y-%m-%d')
                elif 'Y / N choice radio' in col:
                    choice = st.radio(col, ['Y', 'N'], key=f'radio_{col}', index=['Y', 'N'].index(existing_value) if existing_value in ['Y', 'N'] else 0)
                    section_data[col] = choice
                elif 'document upload / display' in col or 'photo upload / picture display' in col:
                    uploaded_file = st.file_uploader(col, key=f'file_{col}')
                    if uploaded_file:
                        # Here, you should handle file saving/uploading as per your requirements
                        section_data[col] = uploaded_file.name
                    elif existing_value:
                        st.write(f"Current file: {existing_value}")
                        section_data[col] = existing_value
                elif 'number input field' in col:
                    try:
                        default_value = float(existing_value) if existing_value else 0.0
                    except ValueError:
                        default_value = 0.0
                    number_value = st.number_input(col, value=default_value, min_value=0.0, step=0.01, key=f'number_{col}')
                    section_data[col] = number_value
                elif 'drop down' in col or 'enum' in col:
                    # For simplicity, treat as text input. In a real-world scenario, you'd want to populate this with actual options.
                    input_value = st.text_input(col, value=str(existing_value), key=f'dropdown_{col}')
                    section_data[col] = input_value
                else:
                    input_value = st.text_input(col, value=str(existing_value), key=f'text_{col}')
                    section_data[col] = input_value
        except sqlite3.Error as e:
            logging.error(f"Error collecting section input: {e}")
            st.error("Failed to collect section input.")
    else:
        st.error("Database connection not available.")
    return section_data

# Display More Apps
def display_more_apps():
    st.title("More phi_apps")
    
    # Define the apps
    apps = [
        {
            "#": 1,
            "app_name": "Attendance App",
            "app_link": "https://example.com/attendance",
            "app_note": "Track your daily attendance."
        },
        {
            "#": 2,
            "app_name": "Leave Request App",
            "app_link": "https://example.com/leave-request",
            "app_note": "Submit and track your leave requests."
        },
        {
            "#": 3,
            "app_name": "Salary Advance Request App",
            "app_link": "https://example.com/salary-advance",
            "app_note": "Request for salary advances."
        },
        {
            "#": 4,
            "app_name": "HR Grievance App",
            "app_link": "https://example.com/hr-grievance",
            "app_note": "File and manage HR grievances."
        },
    ]
    
    # Create DataFrame
    df_apps = pd.DataFrame(apps)

    # Display the table
    st.table(df_apps)

    st.markdown("""
    ### Available Applications
    - **Attendance App:** [Access Here](https://example.com/attendance)
    - **Leave Request App:** [Access Here](https://example.com/leave-request)
    - **Salary Advance Request App:** [Access Here](https://example.com/salary-advance)
    - **HR Grievance App:** [Access Here](https://example.com/hr-grievance)
    """)


# Display Section Details
def display_section(employee_data, start_col, end_col, editable=False):
    conn = get_connection()
    if conn:
        try:
            df_columns = pd.read_sql_query('PRAGMA table_info(employee_center)', conn)
            columns = df_columns['name'].tolist()

            start_idx = columns.index(start_col) + 1 if start_col in columns else 0
            end_idx = columns.index(end_col) if end_col in columns else len(columns)
            section_columns = columns[start_idx:end_idx]

            for col in section_columns:
                if col in employee_data:
                    value = employee_data[col]
                    if col == 'Photograph':
                        continue  # Handled separately
                    if not editable:
                        # View-only display
                        st.markdown(f"**{col}**: {value}")
        except sqlite3.Error as e:
            logging.error(f"Error fetching section columns: {e}")
            st.error("Failed to retrieve section details.")
    else:
        st.error("Database connection not available.")


# Display Performance Reviews
def display_performance_reviews(employee_data, start_col, end_col):
    conn = get_connection()
    if conn:
        try:
            df_columns = pd.read_sql_query('PRAGMA table_info(employee_center)', conn)
            columns = df_columns['name'].tolist()

            start_idx = columns.index(start_col) + 1 if start_col in columns else 0
            end_idx = columns.index(end_col) if end_col in columns else len(columns)
            section_columns = columns[start_idx:end_idx]

            review_columns = [col for col in section_columns if col.startswith('Review#')]
            review_numbers = sorted(set([col.split()[0] for col in review_columns]))

            for review_number in review_numbers:
                with st.container():
                    st.subheader(f"{review_number}")
                    cols = st.columns(2)
                    for idx, col in enumerate(review_columns):
                        if col.startswith(review_number):
                            value = employee_data.get(col, '')
                            cols[idx % 2].markdown(f"**{col}**: {value}")
        except sqlite3.Error as e:
            logging.error(f"Error fetching performance reviews: {e}")
            st.error("Failed to retrieve performance reviews.")
    else:
        st.error("Database connection not available.")


# Display Salary Breakup
def display_salary_breakup(employee_data):
    salary_columns = [
        'Basic AMOUNT', 'House Rent Allowance (HRA) AMOUNT', 'Conveyance Allowance AMOUNT',
        'Medical Allowance AMOUNT', 'Special Allowance AMOUNT', 'Performance Award AMOUNT',
        'Bonus AMOUNT'
    ]

    amounts = []
    for col in salary_columns:
        amount = clean_salary(employee_data.get(col, 0))
        amounts.append(amount)

    df_salary = pd.DataFrame({
        'Component': [col.replace(' AMOUNT', '') for col in salary_columns],
        'Amount': amounts
    })

    col1, col2 = st.columns(2)
    with col1:
        st.bar_chart(df_salary.set_index('Component'))
    with col2:
        st.table(df_salary)

# Save Employee Changes
def save_employee_changes(euid, updated_data):
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            set_clause = ", ".join([f'"{col}" = ?' for col in updated_data.keys()])
            values = tuple(updated_data.values()) + (euid,)
            query = f'UPDATE employee_center SET {set_clause} WHERE "Employee UID# (EUID#)" = ?'
            cursor.execute(query, values)
            conn.commit()
            logging.info(f"Employee data updated for EUID# {euid}")
            return True
        except sqlite3.Error as e:
            logging.error(f"Failed to update employee data: {e}")
            return False
    else:
        st.error("Database connection not available.")
        return False

# Run the app
if __name__ == '__main__':
    main()
'''


import streamlit as st
import pandas as pd
import sqlite3
import re
from datetime import datetime, date
import logging
import bcrypt
import requests
from io import BytesIO
from PIL import Image
from dateutil import parser

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set page configuration
st.set_page_config(page_title="Employee Centre", layout="wide", initial_sidebar_state="collapsed")

# Apply custom CSS
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        logging.error(f"CSS file {file_name} not found.")
        st.error(f"CSS file {file_name} not found.")

local_css("assets/styles.css")

# Database connection
@st.cache_resource
def get_connection():
    try:
        conn = sqlite3.connect('database/employee_center.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection failed: {e}")
        st.error("Failed to connect to the database.")
        return None

# Load employee data
@st.cache_data
def load_employee_data():
    conn = get_connection()
    if conn:
        try:
            df = pd.read_sql_query("SELECT * FROM employee_center", conn)
            df['Employee UID# (EUID#)'] = pd.to_numeric(df['Employee UID# (EUID#)'], errors='coerce').astype('Int64')
            string_cols = df.select_dtypes(['object']).columns
            df[string_cols] = df[string_cols].apply(lambda x: x.str.strip())
            return df
        except sqlite3.Error as e:
            logging.error(f"Failed to load employee data: {e}")
            st.error("Failed to load employee data.")
            return pd.DataFrame()
    else:
        return pd.DataFrame()

# Helper function to clean and convert salary strings to float
def clean_salary(salary_str):
    if isinstance(salary_str, str):
        cleaned_str = re.sub(r'[^\d.]', '', salary_str)
        return float(cleaned_str) if cleaned_str else 0.0
    elif isinstance(salary_str, (int, float)):
        return salary_str
    else:
        return 0.0

# User Authentication
def authenticate(username, pin):
    df = load_employee_data()
    if df.empty:
        logging.warning("Employee data is empty. Authentication failed.")
        return False
    user = df[df['Employee UID# (EUID#)'] == username]
    if not user.empty:
        stored_pin = user.iloc[0]['PIN']
        if stored_pin:
            if stored_pin.startswith('$2b$') or stored_pin.startswith('$2a$'):
                try:
                    return bcrypt.checkpw(pin.encode('utf-8'), stored_pin.encode('utf-8'))
                except ValueError as ve:
                    logging.error(f"Bcrypt error: {ve}")
                    return False
            else:
                return pin == stored_pin
    return False

# Main Application
def main():
    # Top bar with Logout button
    logout_button_container = st.container()
    with logout_button_container:
        col1, col2 = st.columns([9,1])
        with col1:
            st.title("Employee Centre")
        with col2:
            if st.session_state.get('auth_status', False):
                # Styled Logout Button
                if st.button("Logout", key="logout_button", help="Logout"):
                    st.session_state.auth_status = False
                    st.session_state.username = None
                    st.rerun()

    # Initialize session state
    if 'auth_status' not in st.session_state:
        st.session_state.auth_status = False
        st.session_state.username = None

    # User Authentication
    if not st.session_state.auth_status:
        st.markdown("### Please Log In")
        employee_uids = load_employee_data()['Employee UID# (EUID#)'].dropna().unique().tolist()
        if employee_uids:
            username = st.selectbox("Select EUID#", options=employee_uids)
        else:
            username = st.text_input("Enter EUID#")
        pin = st.text_input("Enter PIN", type="password")
        if st.button("Login"):
            if authenticate(username, pin):
                st.session_state.auth_status = True
                st.session_state.username = username
                employee_full_name = load_employee_data().loc[load_employee_data()['Employee UID# (EUID#)'] == username, 'Employee Full Name'].values[0]
                # Display toast-like notification
                st.success(f"Logged in as EUID# {username} | {employee_full_name}", icon="✅")
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        # Display toast-like notification
        employee_full_name = load_employee_data().loc[load_employee_data()['Employee UID# (EUID#)'] == st.session_state.username, 'Employee Full Name'].values[0]
        st.toast(f"Logged in as EUID# {st.session_state.username} | {employee_full_name}", icon="✅")

        # Main Application Logic
        display_dashboard()

# Dashboard
def display_dashboard():
    st.title("Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.image("https://pic.onlinewebfonts.com/thumbnails/icons_331521.svg", width=200)
        if st.button("View Profile"):
            st.session_state.current_page = "view_profile"
            st.rerun()

    with col2:
        st.image("https://pic.onlinewebfonts.com/thumbnails/icons_568816.svg", width=200)
        if st.button("Edit Profile"):
            st.session_state.current_page = "edit_profile"
            st.rerun()

    with col3:
        st.image("https://pic.onlinewebfonts.com/thumbnails/icons_523333.svg", width=200)
        if st.button("More phi_apps"):
            st.session_state.current_page = "more_apps"
            st.rerun()

    if 'current_page' in st.session_state:
        if st.session_state.current_page == "view_profile":
            view_employee_profile()
        elif st.session_state.current_page == "edit_profile":
            edit_employee_profile()
        elif st.session_state.current_page == "more_apps":
            display_more_apps()

# View Employee Profile
def view_employee_profile():
    st.title("View Profile")
    logging.info("Viewing employee profile")

    df = load_employee_data()
    if df.empty:
        st.error("No employee data available.")
        return

    # Fetch data for the logged-in employee
    username = st.session_state.username
    employee_data = df[df['Employee UID# (EUID#)'] == username]

    if not employee_data.empty:
        employee_data = employee_data.iloc[0]
        st.subheader(f"Employee UID#: {employee_data['Employee UID# (EUID#)']}")
        st.subheader(f"Employee Name: {employee_data['Employee Full Name']}")

        # Display Profile Picture
        photograph_url = employee_data.get('Photograph', None)
        if photograph_url:
            try:
                response = requests.get(photograph_url)
                img = Image.open(BytesIO(response.content))
                st.image(img, width=150, caption="Profile Picture")
            except Exception as e:
                logging.error(f"Failed to load profile picture: {e}")
                st.warning("Profile picture not available.")
        else:
            st.info("No profile picture provided.")

        # Display Sections in Tabs
        tabs = st.tabs([
            "General Details",
            "Definitives",
            "Personal Details",
            "Payroll",
            "Salary Breakup",
            "Career Progression",
            "Performance Reviews"
        ])

        with tabs[0]:
            st.header("General Details")
            display_section(employee_data, 'SECTION- GENERAL DETAILS', 'SECTION- DEFINITIVES')

        with tabs[1]:
            st.header("Definitives")
            display_section(employee_data, 'SECTION- DEFINITIVES', 'SECTION- PERSONAL DETAILS')

        with tabs[2]:
            st.header("Personal Details")
            display_section(employee_data, 'SECTION- PERSONAL DETAILS', 'SECTION- PAYROLL')

        with tabs[3]:
            st.header("Payroll")
            display_section(employee_data, 'SECTION- PAYROLL', 'SECTION- SALARY BREAK UP')

        with tabs[4]:
            st.header("Salary Breakup")
            display_salary_breakup(employee_data)

        with tabs[5]:
            st.header("Career Progression")
            display_section(employee_data, 'SECTION- LCT', 'SECTION- PR')

        with tabs[6]:
            st.header("Performance Reviews")
            display_performance_reviews(employee_data, 'SECTION- PR', None)
    else:
        st.error("Employee data not found.")

# Edit Employee Profile
def edit_employee_profile():
    st.title("Edit Profile")
    logging.info("Editing employee profile")

    df = load_employee_data()
    if df.empty:
        st.error("No employee data available.")
        return

    # Fetch data for the logged-in employee
    username = st.session_state.username
    employee_data = df[df['Employee UID# (EUID#)'] == username]

    if not employee_data.empty:
        employee_data = employee_data.iloc[0].to_dict()
        
        # Define all sections with editability flag
        sections = [
            ('General Details', 'SECTION- GENERAL DETAILS', 'SECTION- DEFINITIVES', True),
            ('Definitives', 'SECTION- DEFINITIVES', 'SECTION- PERSONAL DETAILS', True),
            ('Personal Details', 'SECTION- PERSONAL DETAILS', 'SECTION- PAYROLL', True),
            ('Payroll', 'SECTION- PAYROLL', 'SECTION- SALARY BREAK UP', False),
            ('Salary Breakup', 'SECTION- SALARY BREAK UP', 'SECTION- LCT', False),
            ('Career Progression', 'SECTION- LCT', 'SECTION- PR', False),
            ('Performance Reviews', 'SECTION- PR', None, False)
        ]

        # Create a single set of tabs for all sections
        tabs = st.tabs([section[0] for section in sections])

        with st.form("edit_employee_form"):
            updated_data = {}
            for i, (section_name, start_col, end_col, is_editable) in enumerate(sections):
                with tabs[i]:
                    st.subheader(section_name)
                    if is_editable:
                        # Editable Sections
                        section_data = collect_section_input(start_col, end_col, employee_data)
                        updated_data.update(section_data)
                    else:
                        # Non-Editable Sections (Read-Only Display)
                        display_section(employee_data, start_col, end_col, editable=False)

            submit_button = st.form_submit_button("Save Changes")
            if submit_button:
                if updated_data:
                    if save_employee_changes(username, updated_data):
                        st.success("Your profile has been updated successfully!")
                    else:
                        st.error("Failed to update your profile.")
                else:
                    st.info("No changes to save.")
    else:
        st.error("Employee data not found.")

# Parse Date
def parse_date(date_string):
    if not date_string:
        return None
    try:
        # Try parsing with dateutil
        return parser.parse(date_string).date()
    except (ValueError, TypeError):
        try:
            # Try parsing with a specific format
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except ValueError:
            # If all parsing attempts fail, return None
            return None

# Collect Section Input
def collect_section_input(start_col, end_col, existing_data):
    conn = get_connection()
    section_data = {}
    if conn:
        try:
            df_columns = pd.read_sql_query('PRAGMA table_info(employee_center)', conn)
            columns = df_columns['name'].tolist()

            start_idx = columns.index(start_col) + 1 if start_col in columns else 0
            end_idx = columns.index(end_col) if end_col in columns else len(columns)
            section_columns = columns[start_idx:end_idx]

            for col in section_columns:
                existing_value = existing_data.get(col, '')
                
                if col == 'DIVISION':
                    existing_options = pd.read_sql_query('SELECT DISTINCT "DIVISION" FROM employee_center', conn)['DIVISION'].dropna().tolist()
                    if 'Philocaly Spaces Pvt. Ltd.' not in existing_options:
                        existing_options.insert(0, 'Philocaly Spaces Pvt. Ltd.')
                    selected_value = st.selectbox(col, options=existing_options, key=f'division_{col}', index=(existing_options.index(existing_value) if existing_value in existing_options else 0))
                    new_value = st.text_input('Add new DIVISION (leave blank if not adding new)', key=f'new_division_{col}')
                    if new_value:
                        selected_value = new_value
                    section_data[col] = selected_value
                elif col in ['Date of Joining', 'DOB']:
                    parsed_date = parse_date(str(existing_value))
                    default_date = parsed_date if parsed_date else date.today()
                    date_value = st.date_input(col, default_date, key=f'date_{col}')
                    section_data[col] = date_value.strftime('%Y-%m-%d')
                elif 'Y / N choice radio' in col:
                    choice = st.radio(col, ['Y', 'N'], key=f'radio_{col}', index=['Y', 'N'].index(existing_value) if existing_value in ['Y', 'N'] else 0)
                    section_data[col] = choice
                elif 'document upload / display' in col or 'photo upload / picture display' in col:
                    uploaded_file = st.file_uploader(col, key=f'file_{col}')
                    if uploaded_file:
                        # Here, you should handle file saving/uploading as per your requirements
                        section_data[col] = uploaded_file.name
                    elif existing_value:
                        st.write(f"Current file: {existing_value}")
                        section_data[col] = existing_value
                elif 'number input field' in col:
                    try:
                        default_value = float(existing_value) if existing_value else 0.0
                    except ValueError:
                        default_value = 0.0
                    number_value = st.number_input(col, value=default_value, min_value=0.0, step=0.01, key=f'number_{col}')
                    section_data[col] = number_value
                elif 'drop down' in col or 'enum' in col:
                    # For simplicity, treat as text input. In a real-world scenario, you'd want to populate this with actual options.
                    input_value = st.text_input(col, value=str(existing_value), key=f'dropdown_{col}')
                    section_data[col] = input_value
                else:
                    input_value = st.text_input(col, value=str(existing_value), key=f'text_{col}')
                    section_data[col] = input_value
        except sqlite3.Error as e:
            logging.error(f"Error collecting section input: {e}")
            st.error("Failed to collect section input.")
    else:
        st.error("Database connection not available.")
    return section_data

# Display More Apps
def display_more_apps():
    st.title("More phi_apps")
    
    # Define the apps
    apps = [
        {
            "#": 1,
            "app_name": "Attendance App",
            "app_link": "https://example.com/attendance",
            "app_note": "Track your daily attendance."
        },
        {
            "#": 2,
            "app_name": "Leave Request App",
            "app_link": "https://example.com/leave-request",
            "app_note": "Submit and track your leave requests."
        },
        {
            "#": 3,
            "app_name": "Salary Advance Request App",
            "app_link": "https://example.com/salary-advance",
            "app_note": "Request for salary advances."
        },
        {
            "#": 4,
            "app_name": "HR Grievance App",
            "app_link": "https://example.com/hr-grievance",
            "app_note": "File and manage HR grievances."
        },
    ]
    
    # Create DataFrame
    df_apps = pd.DataFrame(apps)

    # Display the table
    st.table(df_apps)

    st.markdown("""
    ### Available Applications
    - **Attendance App:** [Access Here](https://example.com/attendance)
    - **Leave Request App:** [Access Here](https://example.com/leave-request)
    - **Salary Advance Request App:** [Access Here](https://example.com/salary-advance)
    - **HR Grievance App:** [Access Here](https://example.com/hr-grievance)
    """)

# Display Section Details
def display_section(employee_data, start_col, end_col, editable=False):
    conn = get_connection()
    if conn:
        try:
            df_columns = pd.read_sql_query('PRAGMA table_info(employee_center)', conn)
            columns = df_columns['name'].tolist()

            start_idx = columns.index(start_col) + 1 if start_col in columns else 0
            end_idx = columns.index(end_col) if end_col in columns else len(columns)
            section_columns = columns[start_idx:end_idx]

            for col in section_columns:
                if col in employee_data:
                    value = employee_data[col]
                    if col == 'Photograph':
                        continue  # Handled separately
                    if not editable:
                        # View-only display
                        st.markdown(f"**{col}**: {value}")
        except sqlite3.Error as e:
            logging.error(f"Error fetching section columns: {e}")
            st.error("Failed to retrieve section details.")
    else:
        st.error("Database connection not available.")

# Display Performance Reviews
def display_performance_reviews(employee_data, start_col, end_col):
    conn = get_connection()
    if conn:
        try:
            df_columns = pd.read_sql_query('PRAGMA table_info(employee_center)', conn)
            columns = df_columns['name'].tolist()

            start_idx = columns.index(start_col) + 1 if start_col in columns else 0
            end_idx = columns.index(end_col) if end_col in columns else len(columns)
            section_columns = columns[start_idx:end_idx]

            review_columns = [col for col in section_columns if col.startswith('Review#')]
            review_numbers = sorted(set([col.split()[0] for col in review_columns]))

            for review_number in review_numbers:
                with st.container():
                    st.subheader(f"{review_number}")
                    cols = st.columns(2)
                    for idx, col in enumerate(review_columns):
                        if col.startswith(review_number):
                            value = employee_data.get(col, '')
                            cols[idx % 2].markdown(f"**{col}**: {value}")
        except sqlite3.Error as e:
            logging.error(f"Error fetching performance reviews: {e}")
            st.error("Failed to retrieve performance reviews.")
    else:
        st.error("Database connection not available.")

# Display Salary Breakup
def display_salary_breakup(employee_data):
    salary_columns = [
        'Basic AMOUNT', 'House Rent Allowance (HRA) AMOUNT', 'Conveyance Allowance AMOUNT',
        'Medical Allowance AMOUNT', 'Special Allowance AMOUNT', 'Performance Award AMOUNT',
        'Bonus AMOUNT'
    ]

    amounts = []
    for col in salary_columns:
        amount = clean_salary(employee_data.get(col, 0))
        amounts.append(amount)

    df_salary = pd.DataFrame({
        'Component': [col.replace(' AMOUNT', '') for col in salary_columns],
        'Amount': amounts
    })

    col1, col2 = st.columns(2)
    with col1:
        st.bar_chart(df_salary.set_index('Component'))
    with col2:
        st.table(df_salary)

# Save Employee Changes
def save_employee_changes(euid, updated_data):
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            set_clause = ", ".join([f'"{col}" = ?' for col in updated_data.keys()])
            values = tuple(updated_data.values()) + (euid,)
            query = f'UPDATE employee_center SET {set_clause} WHERE "Employee UID# (EUID#)" = ?'
            cursor.execute(query, values)
            conn.commit()
            logging.info(f"Employee data updated for EUID# {euid}")
            return True
        except sqlite3.Error as e:
            logging.error(f"Failed to update employee data: {e}")
            return False
    else:
        st.error("Database connection not available.")
        return False

# Run the app
if __name__ == '__main__':
    main()
