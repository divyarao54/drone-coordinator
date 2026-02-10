from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from api.services.sheets_service import SheetsService
from api.services.matching_service import MatchingService
from api.models.pilot import Pilot
from api.models.drone import Drone
from api.models.mission import Mission

logger = logging.getLogger(__name__)

class AssignmentTracker:
    """Agent for tracking and managing assignments"""
    
    def __init__(self, sheets_service: SheetsService, matching_service: MatchingService):
        self.sheets_service = sheets_service
        self.matching_service = matching_service
    
    def handle_query(self, query: str) -> str:
        """Handle assignment-related queries"""
        if "assign" in query.lower() and "mission" in query.lower():
            return self.suggest_assignments(query)
        elif "current" in query.lower() and "assignment" in query.lower():
            return self.get_current_assignments()
        elif "match" in query.lower():
            return self.find_matches_for_mission(query)
        else:
            return self.get_assignment_summary()
    
    def suggest_assignments(self, query: str) -> str:
        """Suggest assignments for missions"""
        missions = self.sheets_service.get_missions()
        pilots = self.sheets_service.get_pilots()
        drones = self.sheets_service.get_drones()
        
        # Find unassigned missions
        unassigned_missions = [m for m in missions if not m.assigned_pilot]
        
        if not unassigned_missions:
            return "All missions are currently assigned."
        
        response = "**Assignment Suggestions**\n\n"
        
        for mission in unassigned_missions[:3]:  # Show top 3
            response += f"**Mission: {mission.project_id} - {mission.client}**\n"
            response += f"Location: {mission.location}, Priority: {mission.priority}\n"
            response += f"Dates: {mission.start_date} to {mission.end_date}\n"
            response += f"Required: {', '.join(mission.required_skills)} | {', '.join(mission.required_certs)}\n\n"
            
            # Find matching pilots
            matching_pilots = self.matching_service.find_matching_pilots(mission, pilots)
            matching_drones = self.matching_service.find_matching_drones(mission, drones)
            
            if matching_pilots and matching_drones:
                # Suggest best match
                best_pilot = matching_pilots[0]
                best_drone = matching_drones[0]
                
                response += f"**Suggested Assignment:**\n"
                response += f"Pilot: {best_pilot.name} ({best_pilot.pilot_id})\n"
                response += f"Drone: {best_drone.drone_id} ({best_drone.model})\n"
                response += f"\nTo assign, use: `assign {mission.project_id} {best_pilot.pilot_id} {best_drone.drone_id}`\n"
            else:
                response += f"❌ No suitable resources available for this mission.\n"
            
            response += "\n" + "-"*50 + "\n\n"
        
        return response
    
    def get_current_assignments(self) -> str:
        """Get current assignments"""
        missions = self.sheets_service.get_missions()
        pilots = self.sheets_service.get_pilots()
        drones = self.sheets_service.get_drones()
        
        assigned_missions = [m for m in missions if m.assigned_pilot]
        
        if not assigned_missions:
            return "No current assignments."
        
        response = "**Current Assignments**\n\n"
        
        for mission in assigned_missions:
            pilot = next((p for p in pilots if p.pilot_id == mission.assigned_pilot), None)
            drone = next((d for d in drones if d.drone_id == mission.assigned_drone), None)
            
            response += f"**{mission.project_id} - {mission.client}**\n"
            response += f"📍 {mission.location} | ⚡ {mission.priority}\n"
            response += f"📅 {mission.start_date} to {mission.end_date}\n"
            
            if pilot:
                response += f"👨‍✈️ Pilot: {pilot.name} ({pilot.pilot_id})\n"
            if drone:
                response += f"🚁 Drone: {drone.drone_id} ({drone.model})\n"
            
            response += "\n" + "-"*40 + "\n\n"
        
        return response
    
    def find_matches_for_mission(self, query: str) -> str:
        """Find matching resources for a specific mission"""
        missions = self.sheets_service.get_missions()
        pilots = self.sheets_service.get_pilots()
        drones = self.sheets_service.get_drones()
        
        # Extract mission ID from query
        target_mission = None
        for mission in missions:
            if mission.project_id.lower() in query.lower() or mission.client.lower() in query.lower():
                target_mission = mission
                break
        
        if not target_mission:
            return "Please specify which mission you're looking for (e.g., 'matches for PRJ001')."
        
        response = f"**Matching Resources for {target_mission.project_id}**\n\n"
        response += f"Client: {target_mission.client}\n"
        response += f"Location: {target_mission.location}\n"
        response += f"Priority: {target_mission.priority}\n"
        response += f"Required Skills: {', '.join(target_mission.required_skills)}\n"
        response += f"Required Certs: {', '.join(target_mission.required_certs)}\n\n"
        
        # Find matching pilots
        matching_pilots = self.matching_service.find_matching_pilots(target_mission, pilots)
        
        response += f"**Matching Pilots ({len(matching_pilots)})**\n"
        if matching_pilots:
            for i, pilot in enumerate(matching_pilots[:5], 1):  # Show top 5
                response += f"{i}. {pilot.name} ({pilot.pilot_id})\n"
                response += f"   Skills: {', '.join(pilot.skills)}\n"
                response += f"   Certs: {', '.join(pilot.certifications)}\n"
                response += f"   Location: {pilot.location}, Status: {pilot.status}\n\n"
        else:
            response += "❌ No matching pilots found.\n\n"
        
        # Find matching drones
        matching_drones = self.matching_service.find_matching_drones(target_mission, drones)
        
        response += f"**Matching Drones ({len(matching_drones)})**\n"
        if matching_drones:
            for i, drone in enumerate(matching_drones[:5], 1):
                response += f"{i}. {drone.drone_id} ({drone.model})\n"
                response += f"   Capabilities: {', '.join(drone.capabilities)}\n"
                response += f"   Location: {drone.location}, Status: {drone.status}\n"
                if drone.maintenance_due:
                    days_until = (drone.maintenance_due - datetime.now().date()).days
                    response += f"   Maintenance: {drone.maintenance_due} ({days_until} days)\n"
                response += "\n"
        else:
            response += "❌ No matching drones found.\n"
        
        return response
    
    def get_assignment_summary(self) -> str:
        """Get assignment summary"""
        missions = self.sheets_service.get_missions()
        
        assigned_count = sum(1 for m in missions if m.assigned_pilot)
        unassigned_count = len(missions) - assigned_count
        
        # Group by priority
        priority_groups = {}
        for mission in missions:
            priority_groups.setdefault(mission.priority, {"total": 0, "assigned": 0})
            priority_groups[mission.priority]["total"] += 1
            if mission.assigned_pilot:
                priority_groups[mission.priority]["assigned"] += 1
        
        response = "**Assignment Summary**\n\n"
        response += f"Total Missions: {len(missions)}\n"
        response += f"Assigned: {assigned_count}\n"
        response += f"Unassigned: {unassigned_count}\n\n"
        
        response += "**By Priority:**\n"
        for priority in ["Urgent", "High", "Standard", "Low"]:
            if priority in priority_groups:
                data = priority_groups[priority]
                assigned_pct = (data["assigned"] / data["total"]) * 100 if data["total"] > 0 else 0
                response += f"{priority}: {data['assigned']}/{data['total']} ({assigned_pct:.0f}% assigned)\n"
        
        # Upcoming assignments
        today = datetime.now().date()
        upcoming_missions = [
            m for m in missions 
            if not m.assigned_pilot and m.start_date >= today
        ]
        
        if upcoming_missions:
            upcoming_missions.sort(key=lambda x: x.start_date)
            response += "\n**Upcoming Unassigned Missions:**\n"
            for mission in upcoming_missions[:3]:
                days_until = (mission.start_date - today).days
                response += f"- {mission.project_id}: Starts in {days_until} days ({mission.start_date})\n"
        
        return response
    
    def create_assignment(self, project_id: str, pilot_id: str, drone_id: str) -> Dict[str, Any]:
        """Create a new assignment"""
        try:
            success = self.sheets_service.assign_to_mission(project_id, pilot_id, drone_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Successfully assigned {pilot_id} and {drone_id} to {project_id}"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to create assignment"
                }
        except Exception as e:
            logger.error(f"Error creating assignment: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }