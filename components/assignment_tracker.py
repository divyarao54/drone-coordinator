import streamlit as st
import pandas as pd
from datetime import datetime
from utils.api_client import call_api

def display_assignment_tracking():
    """Display assignment tracking interface"""
    st.title("🔗 Assignment Tracking")
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Current Assignments", "Assignment History", "Reassignments"])
    
    with tab1:
        display_current_assignments()
    
    with tab2:
        display_assignment_history()
    
    with tab3:
        display_reassignment_interface()

def display_current_assignments():
    """Display current active assignments"""
    st.subheader("📋 Current Assignments")
    
    assignments = call_api("/assignments")
    
    if assignments:
        # Create DataFrame for display
        data = []
        for assignment in assignments:
            data.append({
                "Mission ID": assignment["project_id"],
                "Client": assignment["client"],
                "Pilot": f"{assignment['assigned_pilot']['name']} ({assignment['assigned_pilot']['pilot_id']})",
                "Drone": f"{assignment['assigned_drone']['drone_id']} ({assignment['assigned_drone']['model']})",
                "Location": assignment["location"],
                "Dates": f"{assignment['start_date']} to {assignment['end_date']}",
                "Priority": assignment["priority"],
                "Status": assignment["status"]
            })
        
        df = pd.DataFrame(data)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            location_filter = st.multiselect(
                "Filter by Location",
                options=df["Location"].unique(),
                default=df["Location"].unique()[:2]
            )
        
        with col2:
            priority_filter = st.multiselect(
                "Filter by Priority",
                options=df["Priority"].unique(),
                default=df["Priority"].unique()
            )
        
        with col3:
            status_filter = st.multiselect(
                "Filter by Status",
                options=df["Status"].unique(),
                default=df["Status"].unique()
            )
        
        # Apply filters
        filtered_df = df
        if location_filter:
            filtered_df = filtered_df[filtered_df["Location"].isin(location_filter)]
        if priority_filter:
            filtered_df = filtered_df[filtered_df["Priority"].isin(priority_filter)]
        if status_filter:
            filtered_df = filtered_df[filtered_df["Status"].isin(status_filter)]
        
        # Display table
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        
        # Assignment statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Assignments", len(assignments))
        with col2:
            active = sum(1 for a in assignments if a["status"] == "Active")
            st.metric("Active", active)
        with col3:
            high_priority = sum(1 for a in assignments if a["priority"] == "High")
            st.metric("High Priority", high_priority)
        with col4:
            urgent = sum(1 for a in assignments if a["priority"] == "Urgent")
            st.metric("Urgent", urgent)
        
        # Assignment details view
        st.subheader("📊 Assignment Details")
        selected_assignment = st.selectbox(
            "Select assignment for details",
            [f"{a['project_id']} - {a['client']}" for a in assignments]
        )
        
        if selected_assignment:
            assignment_id = selected_assignment.split(" - ")[0]
            assignment = next((a for a in assignments if a["project_id"] == assignment_id), None)
            
            if assignment:
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Mission Details:**")
                    st.write(f"**Client:** {assignment['client']}")
                    st.write(f"**Location:** {assignment['location']}")
                    st.write(f"**Priority:** {assignment['priority']}")
                    st.write(f"**Dates:** {assignment['start_date']} to {assignment['end_date']}")
                
                with col2:
                    st.write("**Assigned Resources:**")
                    st.write(f"**Pilot:** {assignment['assigned_pilot']['name']}")
                    st.write(f"**Skills:** {', '.join(assignment['assigned_pilot']['skills'])}")
                    st.write(f"**Drone:** {assignment['assigned_drone']['model']}")
                    st.write(f"**Capabilities:** {', '.join(assignment['assigned_drone']['capabilities'])}")
    
    else:
        st.info("No current assignments found.")

def display_assignment_history():
    """Display assignment history"""
    st.subheader("📜 Assignment History")
    
    # This would typically come from a database
    # For now, show sample history
    st.info("Assignment history feature requires database integration.")
    
    # Sample history table
    history_data = [
        {
            "Mission": "PRJ001",
            "Client": "Client A",
            "Pilot": "Arjun → Rohit",
            "Drone": "D001 → D003",
            "Changed On": "2024-01-15",
            "Reason": "Pilot availability"
        },
        {
            "Mission": "PRJ002", 
            "Client": "Client B",
            "Pilot": "Neha",
            "Drone": "D002",
            "Changed On": "2024-01-10",
            "Reason": "Initial assignment"
        }
    ]
    
    df = pd.DataFrame(history_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

def display_reassignment_interface():
    """Display reassignment interface"""
    st.subheader("🔄 Reassignment Management")
    
    # Get current assignments
    assignments = call_api("/assignments")
    
    if assignments:
        # Select assignment to reassign
        assignment_options = [f"{a['project_id']} - {a['client']}" for a in assignments]
        selected_assignment = st.selectbox("Select assignment to reassign", assignment_options)
        
        if selected_assignment:
            assignment_id = selected_assignment.split(" - ")[0]
            assignment = next((a for a in assignments if a["project_id"] == assignment_id), None)
            
            if assignment:
                st.write("**Current Assignment:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Current Pilot:** {assignment['assigned_pilot']['name']}")
                    st.write(f"**Skills:** {', '.join(assignment['assigned_pilot']['skills'])}")
                
                with col2:
                    st.write(f"**Current Drone:** {assignment['assigned_drone']['model']}")
                    st.write(f"**Capabilities:** {', '.join(assignment['assigned_drone']['capabilities'])}")
                
                st.divider()
                
                # Reassignment options
                st.subheader("🔄 Select New Resources")
                
                # Get available pilots and drones for this mission
                available_pilots = call_api(f"/missions/{assignment_id}/available-pilots")
                available_drones = call_api(f"/missions/{assignment_id}/available-drones")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Available Pilots:**")
                    if available_pilots:
                        pilot_options = [f"{p['name']} ({p['pilot_id']})" for p in available_pilots]
                        new_pilot = st.selectbox("Select new pilot", pilot_options)
                    else:
                        st.warning("No pilots available")
                        new_pilot = None
                
                with col2:
                    st.write("**Available Drones:**")
                    if available_drones:
                        drone_options = [f"{d['drone_id']} ({d['model']})" for d in available_drones]
                        new_drone = st.selectbox("Select new drone", drone_options)
                    else:
                        st.warning("No drones available")
                        new_drone = None
                
                # Reassignment reason
                reason = st.text_area("Reason for reassignment", 
                                    placeholder="E.g., Pilot unavailable, Drone maintenance, etc.")
                
                # Perform reassignment
                if st.button("🔄 Execute Reassignment", type="primary"):
                    if new_pilot and new_drone:
                        # Extract IDs
                        pilot_id = new_pilot.split('(')[1].replace(')', '')
                        drone_id = new_drone.split('(')[0].strip()
                        
                        # Call reassignment API
                        result = call_api(f"/assignments/{assignment_id}/reassign", "PUT", {
                            "pilot_id": pilot_id,
                            "drone_id": drone_id,
                            "reason": reason
                        })
                        
                        if result:
                            st.success("✅ Reassignment successful!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("Reassignment failed. Check for conflicts.")
                    else:
                        st.error("Please select both a pilot and a drone")
    else:
        st.info("No assignments to reassign.")