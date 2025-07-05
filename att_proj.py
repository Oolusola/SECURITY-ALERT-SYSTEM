import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from datetime import datetime
from geopy.distance import geodesic
import gspread

st.set_page_config(page_title="Attendance Logger", layout="centered")
st.title("📋 STH Facility Attendant Form")

# Sample facility data
facility_data = [
    {"Facility": "State office", "Landmark": "Kaduna North", "Latitude": 10.51508777, "Longitude": 7.43844, "Postal code": "800283", "LGA": "Kaduna North"},
    {"Facility": "Amina Hospital", "Landmark": "Chikun", "Latitude": 10.4554067, "Longitude": 7.4258814, "Postal code": "800282", "LGA": "Chikun"},
    {"Facility": "Sabon Tasha General Hospital", "Landmark": "Chikun", "Latitude": 10.4489626, "Longitude": 7.478136, "Postal code": "800104", "LGA": "Chikun"},
    {"Facility": "Kujama Rural Hospital", "Landmark": "Kaduna South", "Latitude": 10.4061661, "Longitude": 7.704165, "Postal code": "802130", "LGA": "Kaduna South"},
]

# --- Inputs ---
name = st.text_input("👤 Enter your name")
facility_names = [f["Facility"] for f in facility_data]
selected_facility_name = st.selectbox("🏥 Select your facility", facility_names)

col1, col2 = st.columns(2)
with col1:
    designation_options = [
        "I3TR", "TSP", "EDC", "M&E officer", "case manager", "adhrnce nurse", "Data clrk", "focal person"
    ]
    designation = st.selectbox("👨‍💼 Select your designation", designation_options)

with col2:
    today = datetime.now().date()
    min_date = datetime(2025, 1, 1).date()
    selected_date = st.date_input("📅 Select today's date", today, min_value=min_date, max_value=today)

# --- Manual Fallback ---
with st.expander("📍 Get My Location Manually"):
    st.markdown("""
    If automatic GPS is slow or blocked, click below to open an external site, copy your location, and paste it here.
    """)
    gps_url = "https://gps-coordinates.org/my-location.php"
    st.markdown(f"[🌐 Open GPS Website]({gps_url})", unsafe_allow_html=True)

    col_lat, col_lon = st.columns(2)
    with col_lat:
        manual_lat = st.text_input("🔢 Latitude (from website)", "")
    with col_lon:
        manual_lon = st.text_input("🔢 Longitude (from website)", "")

    if manual_lat and manual_lon:
        st.success(f"📍 Manual Location Set: Latitude {manual_lat}, Longitude {manual_lon}")

# --- Try Auto GPS (button after manual) ---
get_location = st.button("📍 Get My Location Automatically")
location = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition", key="get_location")

if get_location:
    if location is None:
        st.info("🛰 Waiting for GPS... Make sure location is enabled in your browser.")
    elif isinstance(location, dict) and 'coords' in location:
        lat = location['coords']['latitude']
        lon = location['coords']['longitude']
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_coord = (lat, lon)

        selected_facility = next((f for f in facility_data if f["Facility"] == selected_facility_name), None)

        st.success("✅ Location detected!")
        st.info(f"**Latitude:** {lat}")
        st.info(f"**Longitude:** {lon}")
        st.info(f"**Timestamp:** {timestamp}")

        with st.expander("📍 Your Info Summary"):
            st.markdown(f"""
            - **Name:** {name}  
            - **Selected Facility:** {selected_facility_name}  
            - **Landmark:** {selected_facility['Landmark']}  
            - **Postal Code:** {selected_facility['Postal code']}  
            - **LGA:** {selected_facility['LGA']}  
            - **Designation:** {designation}  
            - **Date:** {selected_date}  
            - **Time:** {timestamp}  
            - **Latitude:** {lat}  
            - **Longitude:** {lon}
            """)
    else:
        st.error("❌ Location access denied or not supported.")

# --- Submit to Google Sheet ---
submit_to_sheet = st.button("✅ Submit Attendance to Google Sheet")

if submit_to_sheet:
    # Use auto GPS if available, else manual
    lat, lon, timestamp = None, None, None
    if get_location and location and isinstance(location, dict) and 'coords' in location:
        lat = location['coords']['latitude']
        lon = location['coords']['longitude']
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elif manual_lat and manual_lon:
        try:
            lat = float(manual_lat)
            lon = float(manual_lon)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            st.error("❌ Invalid manual coordinates provided.")
    else:
        st.error("❌ No location data to submit.")

    if lat and lon:
        selected_facility = next((f for f in facility_data if f["Facility"] == selected_facility_name), None)
        if selected_facility:
            # Calculate distance
            facility_coord = (selected_facility["Latitude"], selected_facility["Longitude"])
            user_coord = (lat, lon)
            distance_km = geodesic(facility_coord, user_coord).km
            if distance_km > 2:
                punctuality_status = "not in the facility"
            else:
                punctuality_status = "arrived at the facility"

            # Prepare row for Google Sheet in the specified order
            row = [
                selected_facility["Facility"],
                selected_facility["Landmark"],
                selected_facility["Postal code"],
                name,
                str(selected_date),
                designation,
                timestamp,
                lat,
                lon,
                punctuality_status,   # Punctuality Check
                round(distance_km, 7) # Distance
            ]
            try:
                from oauth2client.service_account import ServiceAccountCredentials
                scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                creds = ServiceAccountCredentials.from_json_keyfile_name("streamlit-attendance-app.json", scope)
                client = gspread.authorize(creds)
                sheet = client.open("Attendant tracker")
                worksheet = sheet.sheet1
                # Ensure header exists in the specified order
                header = ["Facility Name", "Landmark", "Postal Code", "Name", "Date", "Designation", "Timestamp", "Latitude", "Longitude", "Punctuality Check", "Distance"]
                if worksheet.row_values(1) != header:
                    worksheet.insert_row(header, 1)
                worksheet.append_row(row)
                st.success("✅ Attendance submitted to Google Sheet!")
            except Exception as e:
                error_message = str(e)
                if (
                    'Failed to resolve' in error_message or
                    'NameResolutionError' in error_message or
                    'getaddrinfo failed' in error_message or
                    'Max retries exceeded with url' in error_message
                ):
                    st.error("❌ You don't have network connection, please connect to a stronger network and try again.")
                else:
                    st.error(f"❌ Failed to submit to Google Sheet: {e}")
        else:
            st.error("❌ Facility not found for submission.")
