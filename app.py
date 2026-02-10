import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import random
import sys
import os

# Add components directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'components'))

# Import components
try:
    from components.assignment_tracker import display_assignment_tracking
    from components.drone_inventory import display_drone_inventory
except ImportError:
    # Define placeholder functions if components aren't available
    def display_assignment_tracking():
        st.title("🔗 Assignment Tracking")
        st.info("Assignment tracking components not loaded")
    
    def display_drone_inventory():
        st.title("🚁 Drone Inventory")
        st.info("Drone inventory components not loaded")

# Page configuration
st.set_page_config(
    page_title="Drone Operations Coordinator AI",
    page_icon="🚁",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .assistant-message {
        background-color: #f0f2f6;
    }
    .user-message {
        background-color: #e6f7ff;
    }
    .status-available { color: #28a745; font-weight: bold; }
    .status-assigned { color: #ffc107; font-weight: bold; }
    .status-unavailable { color: #dc3545; font-weight: bold; }
    .priority-high { background-color: #f8d7da; padding: 0.2rem 0.5rem; border-radius: 0.25rem; }
    .priority-urgent { background-color: #dc3545; color: white; padding: 0.2rem 0.5rem; border-radius: 0.25rem; }
</style>
""", unsafe_allow_html=True)

# API URL (adjust for your deployment)
API_URL = "http://localhost:8000"  # Change this for production

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'current_view' not in st.session_state:
    st.session_state.current_view = "dashboard"

def call_api(endpoint, method="GET", data=None):
    """Helper function to call backend API"""
    try:
        url = f"{API_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PUT":
            response = requests.put(url, json=data)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

def display_dashboard():
    """Display main dashboard"""
    st.title("🚁 Drone Operations Coordinator AI")
    
    # Get current stats
    stats = call_api("/stats")
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Available Pilots", stats['available_pilots'], 
                     f"{stats['available_pilots_change']}%")
        with col2:
            st.metric("Available Drones", stats['available_drones'],
                     f"{stats['available_drones_change']}%")
        with col3:
            st.metric("Active Missions", stats['active_missions'])
        with col4:
            st.metric("Pending Assignments", stats['pending_assignments'])
    
    # Quick actions
    st.subheader("📋 Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("👨‍✈️ View All Pilots", use_container_width=True):
            st.session_state.current_view = "pilots"
            st.rerun()
    
    with col2:
        if st.button("🚁 View All Drones", use_container_width=True):
            st.session_state.current_view = "drones"
            st.rerun()
    
    with col3:
        if st.button("📋 View Missions", use_container_width=True):
            st.session_state.current_view = "missions"
            st.rerun()
    
    with col4:
        if st.button("⚠️ Check Conflicts", use_container_width=True):
            conflicts = call_api("/conflicts")
            if conflicts:
                st.session_state.current_view = "conflicts"
                st.rerun()
    
    # Recent activity
    st.subheader("🔄 Recent Activity")
    activity = call_api("/recent-activity")
    if activity:
        for act in activity[:5]:
            st.info(f"{act['timestamp']}: {act['message']}")

def display_pilots():
    """Display pilot roster"""
    st.title("👨‍✈️ Pilot Roster Management")
    
    # Get pilot data
    pilots = call_api("/pilots")
    if pilots:
        df = pd.DataFrame(pilots)
        
        # Status filter
        status_filter = st.multiselect(
            "Filter by Status",
            options=['Available', 'Assigned', 'On Leave', 'Unavailable'],
            default=['Available', 'Assigned']
        )
        
        if status_filter:
            df = df[df['status'].isin(status_filter)]
        
        # Location filter
        locations = df['location'].unique()
        location_filter = st.multiselect("Filter by Location", options=locations)
        if location_filter:
            df = df[df['location'].isin(location_filter)]
        
        # Display table
        st.dataframe(df, use_container_width=True)
        
        # Update pilot status
        st.subheader("Update Pilot Status")
        col1, col2 = st.columns(2)
        with col1:
            pilot_id = st.selectbox("Select Pilot", df['pilot_id'].tolist())
        with col2:
            new_status = st.selectbox("New Status", 
                                     ['Available', 'Assigned', 'On Leave', 'Unavailable'])
        
        if st.button("Update Status"):
            result = call_api(f"/pilots/{pilot_id}/status", "PUT", {"status": new_status})
            if result:
                st.success(f"Updated {pilot_id} to {new_status}")
                st.rerun()

def display_drones():
    """Display drone inventory"""
    st.title("🚁 Drone Fleet Management")
    
    # Get drone data
    drones = call_api("/drones")
    if drones:
        df = pd.DataFrame(drones)
        
        # Status filter
        status_filter = st.multiselect(
            "Filter by Status",
            options=['Available', 'In Use', 'Maintenance', 'Unavailable'],
            default=['Available', 'In Use']
        )
        
        if status_filter:
            df = df[df['status'].isin(status_filter)]
        
        # Display table
        st.dataframe(df, use_container_width=True)
        
        # Maintenance alerts
        st.subheader("🔧 Maintenance Alerts")
        today = datetime.now().date()
        for _, drone in df.iterrows():
            if drone['maintenance_due']:
                due_date = datetime.strptime(drone['maintenance_due'], '%Y-%m-%d').date()
                days_until = (due_date - today).days
                if days_until <= 7:
                    st.warning(f"Drone {drone['drone_id']} needs maintenance in {days_until} days")

def display_missions():
    """Display missions and assignments"""
    st.title("📋 Mission Management")
    
    # Get mission data
    missions = call_api("/missions")
    if missions:
        df = pd.DataFrame(missions)
        
        # Priority filter
        priority_filter = st.multiselect(
            "Filter by Priority",
            options=['Urgent', 'High', 'Standard', 'Low'],
            default=['Urgent', 'High']
        )
        
        if priority_filter:
            df = df[df['priority'].isin(priority_filter)]
        
        # Display missions
        for _, mission in df.iterrows():
            with st.expander(f"{mission['project_id']} - {mission['client']} ({mission['priority']})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Location:** {mission['location']}")
                    st.write(f"**Dates:** {mission['start_date']} to {mission['end_date']}")
                    st.write(f"**Required Skills:** {mission['required_skills']}")
                    st.write(f"**Required Certs:** {mission['required_certs']}")
                
                with col2:
                    # Get available pilots for this mission
                    available_pilots = call_api(f"/missions/{mission['project_id']}/available-pilots")
                    available_drones = call_api(f"/missions/{mission['project_id']}/available-drones")
                    
                    if available_pilots:
                        st.write("**Available Pilots:**")
                        for pilot in available_pilots[:3]:  # Show top 3
                            st.write(f"• {pilot['name']} ({pilot['skills']})")
                    
                    # Assignment form
                    if st.button(f"Assign Resources", key=f"assign_{mission['project_id']}"):
                        st.session_state.current_view = f"assign_{mission['project_id']}"
                        st.rerun()

def display_new_assignment():
    """Display new assignment interface"""
    st.title("➕ New Assignment")
    
    # Get all missions
    missions = call_api("/missions")
    if not missions:
        st.warning("No missions available. Create a mission first.")
        return
    
    # Mission selection
    st.subheader("1. Select Mission")
    mission_options = [f"{m['project_id']} - {m['client']} ({m['priority']})" for m in missions]
    selected_mission_str = st.selectbox("Choose a mission", mission_options)
    
    if selected_mission_str:
        # Extract mission ID
        mission_id = selected_mission_str.split(' - ')[0]
        
        # Get the selected mission details
        selected_mission = next((m for m in missions if m['project_id'] == mission_id), None)
        
        if selected_mission:
            st.info(f"""
            **Mission Details:**
            - Client: {selected_mission['client']}
            - Location: {selected_mission['location']}
            - Dates: {selected_mission['start_date']} to {selected_mission['end_date']}
            - Required Skills: {selected_mission['required_skills']}
            - Required Certs: {selected_mission['required_certs']}
            """)
            
            # Get available resources for this mission
            available_pilots = call_api(f"/missions/{mission_id}/available-pilots")
            available_drones = call_api(f"/missions/{mission_id}/available-drones")
            
            st.subheader("2. Select Resources")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Available Pilots**")
                if available_pilots:
                    pilot_options = {}
                    for pilot in available_pilots:
                        key = f"{pilot['name']} ({pilot['pilot_id']})"
                        pilot_options[key] = {
                            'id': pilot['pilot_id'],
                            'skills': pilot['skills'],
                            'certs': pilot['certifications'],
                            'location': pilot['location']
                        }
                    
                    selected_pilot_key = st.selectbox(
                        "Choose a pilot",
                        list(pilot_options.keys()),
                        format_func=lambda x: f"{x} - Skills: {pilot_options[x]['skills']}"
                    )
                    
                    if selected_pilot_key:
                        pilot_info = pilot_options[selected_pilot_key]
                        st.write(f"**Skills:** {pilot_info['skills']}")
                        st.write(f"**Certifications:** {pilot_info['certs']}")
                        st.write(f"**Location:** {pilot_info['location']}")
                else:
                    st.warning("No pilots available for this mission")
                    selected_pilot_key = None
            
            with col2:
                st.write("**Available Drones**")
                if available_drones:
                    drone_options = {}
                    for drone in available_drones:
                        key = f"{drone['drone_id']} ({drone['model']})"
                        drone_options[key] = {
                            'id': drone['drone_id'],
                            'capabilities': drone['capabilities'],
                            'location': drone['location'],
                            'maintenance': drone.get('maintenance_due', 'Not due')
                        }
                    
                    selected_drone_key = st.selectbox(
                        "Choose a drone",
                        list(drone_options.keys()),
                        format_func=lambda x: f"{x} - Capabilities: {drone_options[x]['capabilities']}"
                    )
                    
                    if selected_drone_key:
                        drone_info = drone_options[selected_drone_key]
                        st.write(f"**Capabilities:** {drone_info['capabilities']}")
                        st.write(f"**Location:** {drone_info['location']}")
                        st.write(f"**Maintenance:** {drone_info['maintenance']}")
                else:
                    st.warning("No drones available for this mission")
                    selected_drone_key = None
            
            # Assignment button
            st.subheader("3. Confirm Assignment")
            
            if st.button("🔗 Assign Resources", type="primary", use_container_width=True):
                if selected_pilot_key and selected_drone_key:
                    pilot_id = pilot_options[selected_pilot_key]['id']
                    drone_id = drone_options[selected_drone_key]['id']
                    
                    with st.spinner("Making assignment..."):
                        result = call_api("/assign", "POST", {
                            "project_id": mission_id,
                            "pilot_id": pilot_id,
                            "drone_id": drone_id
                        })
                        
                        if result:
                            st.success("✅ Assignment successful!")
                            st.balloons()
                            
                            # Show assignment details
                            st.info(f"""
                            **Assignment Details:**
                            - Mission: {mission_id} ({selected_mission['client']})
                            - Pilot: {selected_pilot_key}
                            - Drone: {selected_drone_key}
                            - Assignment Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                            """)
                            
                            # Option to go to assignments view
                            if st.button("View All Assignments"):
                                st.session_state.current_view = "assignments"
                                st.rerun()
                        else:
                            st.error("Assignment failed. Please check for conflicts.")
                else:
                    st.error("Please select both a pilot and a drone")

def chat_interface():
    """Display conversational interface"""
    st.title("💬 Coordinator Assistant")
    
    # Chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about pilots, drones, missions, or assignments..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = call_api("/chat", "POST", {"message": prompt})
                if response:
                    reply = response.get("response", "I couldn't process that request.")
                else:
                    reply = "Sorry, I'm having trouble connecting to the server."
                
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

def main():
    """Main application"""
    
    # Sidebar navigation
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2972/2972544.png", width=100)
        st.title("Navigation")
        
        view_options = {
            "dashboard": "📊 Dashboard",
            "chat": "💬 Chat Assistant",
            "pilots": "👨‍✈️ Pilots",
            "drones": "🚁 Drone Inventory",  # Changed from "Drones"
            "missions": "📋 Missions",
            "assign": "➕ New Assignment",
            "assignments": "🔗 Assignment Tracking",  # Changed from "Current Assignments"
            "conflicts": "⚠️ Conflicts"
        }
        
        selected = st.radio("Go to", list(view_options.values()))
        
        # Map selection back to view key
        for key, value in view_options.items():
            if value == selected:
                st.session_state.current_view = key
                break
        
        st.divider()
        
        # Sync status
        if st.button("🔄 Sync with Google Sheets", use_container_width=True):
            with st.spinner("Syncing..."):
                result = call_api("/sync", "POST")
                if result:
                    st.success("Sync completed!")
                else:
                    st.error("Sync failed")
        
        # Quick stats
        st.divider()
        st.subheader("System Status")
        stats = call_api("/stats")
        if stats:
            st.write(f"🟢 API: Online")
            st.write(f"📊 Last sync: {stats.get('last_sync', 'N/A')}")
            st.write(f"👨‍✈️ Available pilots: {stats.get('available_pilots', 0)}")
            st.write(f"🚁 Available drones: {stats.get('available_drones', 0)}")
    
    # Display selected view - UPDATE THIS SECTION
    if st.session_state.current_view == "dashboard":
        display_dashboard()
    elif st.session_state.current_view == "pilots":
        display_pilots()
    elif st.session_state.current_view == "drones":
        display_drone_inventory()  # Changed from display_drones()
    elif st.session_state.current_view == "missions":
        display_missions()
    elif st.session_state.current_view == "chat":
        chat_interface()
    elif st.session_state.current_view == "conflicts":
        conflicts = call_api("/conflicts")
        if conflicts:
            st.title("⚠️ Conflict Detection")
            for conflict in conflicts:
                st.error(conflict['message'])
        else:
            st.success("No conflicts detected!")
    elif st.session_state.current_view == "assign":
        display_new_assignment()
    elif st.session_state.current_view == "assignments":
        display_assignment_tracking()  # Changed from display_assignments()

if __name__ == "__main__":
    main()