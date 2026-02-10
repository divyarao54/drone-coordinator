import streamlit as st
import pandas as pd
from datetime import datetime, date
from utils.api_client import call_api

def display_drone_inventory():
    """Display drone inventory management interface"""
    st.title("🚁 Drone Inventory Management")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "Fleet Overview", 
        "Maintenance", 
        "Deployment Status",
        "Search & Filter"
    ])
    
    with tab1:
        display_fleet_overview()
    
    with tab2:
        display_maintenance_tracker()
    
    with tab3:
        display_deployment_status()
    
    with tab4:
        display_search_filters()

def display_fleet_overview():
    """Display complete drone fleet overview"""
    st.subheader("📊 Fleet Overview")
    
    # Get all drones
    drones = call_api("/drones")
    
    if drones:
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_drones = len(drones)
            st.metric("Total Drones", total_drones)
        
        with col2:
            available = sum(1 for d in drones if d['status'] == 'Available')
            st.metric("Available", available)
        
        with col3:
            in_use = sum(1 for d in drones if d['status'] == 'In Use')
            st.metric("In Use", in_use)
        
        with col4:
            maintenance = sum(1 for d in drones if d['status'] == 'Maintenance')
            st.metric("Maintenance", maintenance)
        
        # Drone table
        st.subheader("📋 Drone Details")
        
        # Convert to DataFrame
        df = pd.DataFrame(drones)
        
        # Add maintenance urgency
        today = date.today()
        df['maintenance_urgency'] = df['maintenance_due'].apply(
            lambda x: "OVERDUE" if x and pd.to_datetime(x).date() < today 
            else f"{(pd.to_datetime(x).date() - today).days} days" if x 
            else "Not set"
        )
        
        # Display with filters
        status_filter = st.multiselect(
            "Filter by Status",
            options=df['status'].unique(),
            default=df['status'].unique()
        )
        
        location_filter = st.multiselect(
            "Filter by Location",
            options=df['location'].unique(),
            default=df['location'].unique()
        )
        
        # Apply filters
        filtered_df = df
        if status_filter:
            filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
        if location_filter:
            filtered_df = filtered_df[filtered_df['location'].isin(location_filter)]
        
        # Display table
        st.dataframe(
            filtered_df[['drone_id', 'model', 'capabilities', 'status', 'location', 
                        'current_assignment', 'maintenance_due', 'maintenance_urgency']],
            use_container_width=True,
            hide_index=True
        )
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Status", use_container_width=True):
                st.rerun()
        
        with col2:
            if st.button("🔧 Check Maintenance", use_container_width=True):
                st.session_state.maintenance_tab = True
                st.rerun()
        
        with col3:
            if st.button("➕ Add New Drone", use_container_width=True):
                display_add_drone_form()
    
    else:
        st.error("Could not load drone data")

def display_maintenance_tracker():
    """Display maintenance tracking"""
    st.subheader("🔧 Maintenance Tracker")
    
    # Get maintenance drones
    days_threshold = st.slider("Show drones needing maintenance within (days):", 1, 30, 7)
    maintenance_drones = call_api(f"/drones/maintenance?days_threshold={days_threshold}")
    
    if maintenance_drones:
        # Categorize by urgency
        overdue = [d for d in maintenance_drones if d['days_until_maintenance'] < 0]
        due_soon = [d for d in maintenance_drones if 0 <= d['days_until_maintenance'] <= 3]
        upcoming = [d for d in maintenance_drones if d['days_until_maintenance'] > 3]
        
        # Overdue section
        if overdue:
            st.error(f"🚨 OVERDUE MAINTENANCE ({len(overdue)} drones)")
            for drone in overdue:
                with st.expander(f"🔴 {drone['drone_id']} - {drone['model']} ({abs(drone['days_until_maintenance'])} days overdue)"):
                    display_drone_maintenance_details(drone)
        
        # Due soon section
        if due_soon:
            st.warning(f"⚠️ MAINTENANCE DUE SOON ({len(due_soon)} drones)")
            for drone in due_soon:
                with st.expander(f"🟡 {drone['drone_id']} - {drone['model']} (due in {drone['days_until_maintenance']} days)"):
                    display_drone_maintenance_details(drone)
        
        # Upcoming section
        if upcoming:
            st.info(f"📅 UPCOMING MAINTENANCE ({len(upcoming)} drones)")
            for drone in upcoming:
                with st.expander(f"🟢 {drone['drone_id']} - {drone['model']} (due in {drone['days_until_maintenance']} days)"):
                    display_drone_maintenance_details(drone)
        
        # Maintenance statistics
        st.subheader("📈 Maintenance Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Due", len(maintenance_drones))
        with col2:
            st.metric("Overdue", len(overdue))
        with col3:
            st.metric("Due This Week", len([d for d in maintenance_drones if d['days_until_maintenance'] <= 7]))
        
        # Update maintenance date
        st.subheader("📅 Update Maintenance Date")
        selected_drone = st.selectbox(
            "Select drone to update",
            [f"{d['drone_id']} - {d['model']}" for d in maintenance_drones]
        )
        
        if selected_drone:
            drone_id = selected_drone.split(" - ")[0]
            
            col1, col2 = st.columns(2)
            with col1:
                new_date = st.date_input("New maintenance date", value=date.today())
            
            with col2:
                st.write("")  # Spacing
                st.write("")  # Spacing
                if st.button("Update Maintenance", type="primary"):
                    result = call_api(f"/drones/{drone_id}/maintenance", "PUT", {
                        "maintenance_due": new_date.strftime("%Y-%m-%d")
                    })
                    
                    if result:
                        st.success(f"✅ Maintenance date updated for {drone_id}")
                        st.rerun()
    
    else:
        st.success(f"✅ No drones need maintenance within {days_threshold} days!")

def display_drone_maintenance_details(drone):
    """Display detailed maintenance information for a drone"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Model:** {drone['model']}")
        st.write(f"**Location:** {drone['location']}")
        st.write(f"**Status:** {drone['status']}")
    
    with col2:
        st.write(f"**Current Assignment:** {drone.get('current_assignment', 'None')}")
        st.write(f"**Maintenance Due:** {drone['maintenance_due']}")
        st.write(f"**Capabilities:** {', '.join(drone['capabilities'])}")

def display_deployment_status():
    """Display drone deployment status"""
    st.subheader("📍 Deployment Status")
    
    deployment_data = call_api("/drones/deployment")
    
    if deployment_data:
        # Create status cards
        cols = st.columns(3)
        
        # Group by status
        status_groups = {}
        for drone in deployment_data:
            status = drone['status']
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(drone)
        
        # Display status cards
        for idx, (status, drones) in enumerate(status_groups.items()):
            col_idx = idx % 3
            with cols[col_idx]:
                st.metric(f"{status} Drones", len(drones))
        
        # Deployment map visualization
        st.subheader("🗺️ Deployment Map")
        
        # Group by location
        location_data = {}
        for drone in deployment_data:
            location = drone['location']
            if location not in location_data:
                location_data[location] = []
            location_data[location].append(drone)
        
        # Display location cards
        for location, drones in location_data.items():
            with st.expander(f"📍 {location} ({len(drones)} drones)"):
                for drone in drones:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        status_color = {
                            'Available': '🟢',
                            'In Use': '🟡',
                            'Maintenance': '🔴'
                        }.get(drone['status'], '⚪')
                        
                        st.write(f"{status_color} **{drone['drone_id']}**")
                    
                    with col2:
                        if drone['assigned_to']:
                            st.write(f"Assigned to: {drone['assigned_to']} ({drone['client']})")
                        else:
                            st.write("Available for assignment")
        
        # Deployment table
        st.subheader("📋 Detailed Deployment")
        df = pd.DataFrame(deployment_data)
        st.dataframe(
            df[['drone_id', 'model', 'status', 'location', 'assigned_to', 
                'client', 'mission_dates', 'maintenance_urgency']],
            use_container_width=True,
            hide_index=True
        )
    
    else:
        st.error("Could not load deployment data")

def display_search_filters():
    """Display advanced search and filters"""
    st.subheader("🔍 Search & Filter Drones")
    
    # Search filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        capability = st.selectbox(
            "Capability",
            ["", "Thermal", "LiDAR", "RGB", "Multispectral", "Mapping"]
        )
    
    with col2:
        location = st.selectbox(
            "Location",
            ["", "Bangalore", "Mumbai", "Delhi", "Chennai", "Hyderabad"]
        )
    
    with col3:
        status = st.selectbox(
            "Status",
            ["", "Available", "In Use", "Maintenance", "Unavailable"]
        )
    
    available_only = st.checkbox("Show only available drones")
    
    # Build query parameters
    params = {}
    if capability:
        params["capability"] = capability
    if location:
        params["location"] = location
    if status:
        params["status"] = status
    if available_only:
        params["available_only"] = "true"
    
    if st.button("🔍 Search", type="primary"):
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"/drones/search?{query_string}" if query_string else "/drones/search"
        
        results = call_api(url)
        
        if results:
            st.success(f"Found {len(results)} drones")
            
            # Display results
            df = pd.DataFrame(results)
            st.dataframe(
                df[['drone_id', 'model', 'capabilities', 'status', 'location', 
                    'current_assignment', 'maintenance_due']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No drones found matching your criteria.")

def display_add_drone_form():
    """Display form to add new drone"""
    st.subheader("➕ Add New Drone")
    
    with st.form("add_drone_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            drone_id = st.text_input("Drone ID", value=f"D{len(call_api('/drones')) + 1:03d}")
            model = st.text_input("Model", placeholder="e.g., DJI M300, Autel Evo II")
            location = st.selectbox("Location", ["Bangalore", "Mumbai", "Delhi", "Chennai", "Hyderabad"])
        
        with col2:
            status = st.selectbox("Status", ["Available", "Maintenance", "Unavailable"])
            capabilities = st.multiselect(
                "Capabilities",
                ["Thermal", "LiDAR", "RGB", "Multispectral", "Mapping", "Inspection", "Survey"]
            )
            maintenance_due = st.date_input("Next Maintenance Due", value=date.today())
        
        if st.form_submit_button("Add Drone", type="primary"):
            # Validate inputs
            if not drone_id or not model:
                st.error("Drone ID and Model are required")
            else:
                # Create new drone object
                new_drone = {
                    "drone_id": drone_id,
                    "model": model,
                    "capabilities": capabilities,
                    "status": status,
                    "location": location,
                    "current_assignment": None,
                    "maintenance_due": maintenance_due.strftime("%Y-%m-%d")
                }
                
                st.success(f"Drone {drone_id} added successfully!")
                st.info("Note: Backend API integration needed to save to Google Sheets")