from typing import List, Dict, Any
import logging
from datetime import datetime

from api.services.sheets_service import SheetsService
from api.models.pilot import Pilot

logger = logging.getLogger(__name__)

class RosterManager:
    """Agent for managing pilot roster"""
    
    def __init__(self, sheets_service: SheetsService):
        self.sheets_service = sheets_service
    
    def handle_query(self, query: str) -> str:
        """Handle roster-related queries"""
        pilots = self.sheets_service.get_pilots()
        
        if "available" in query.lower():
            return self.get_availability_report(query)
        elif "skill" in query.lower():
            return self.get_pilots_by_skill(query)
        elif "location" in query.lower():
            return self.get_pilots_by_location(query)
        elif "certification" in query.lower() or "cert" in query.lower():
            return self.get_pilots_by_certification(query)
        else:
            return self.get_roster_summary()
    
    def get_availability_report(self, query: str = "") -> str:
        """Get pilot availability report"""
        pilots = self.sheets_service.get_pilots()
        
        available_pilots = [p for p in pilots if p.status == "Available"]
        assigned_pilots = [p for p in pilots if p.status == "Assigned"]
        on_leave_pilots = [p for p in pilots if p.status == "On Leave"]
        
        response = f"**Pilot Availability Report**\n\n"
        response += f"Total Pilots: {len(pilots)}\n"
        response += f"Available: {len(available_pilots)}\n"
        response += f"Assigned: {len(assigned_pilots)}\n"
        response += f"On Leave: {len(on_leave_pilots)}\n\n"
        
        if available_pilots:
            response += "**Available Pilots:**\n"
            for pilot in available_pilots[:5]:  # Show top 5
                response += f"- {pilot.name} ({pilot.pilot_id}) - {pilot.location} - Skills: {', '.join(pilot.skills)}\n"
        
        return response
    
    def get_pilots_by_skill(self, query: str) -> str:
        """Get pilots with specific skills"""
        pilots = self.sheets_service.get_pilots()
        
        # Extract skill from query (simplified)
        skills_keywords = ["mapping", "survey", "inspection", "thermal"]
        target_skill = None
        
        for skill in skills_keywords:
            if skill in query.lower():
                target_skill = skill
                break
        
        if not target_skill:
            return "Please specify a skill to search for (e.g., 'pilots with mapping skills')."
        
        matching_pilots = [
            p for p in pilots 
            if target_skill in [s.lower() for s in p.skills]
        ]
        
        if matching_pilots:
            response = f"**Pilots with {target_skill.title()} skills:**\n\n"
            for pilot in matching_pilots:
                response += f"- {pilot.name} ({pilot.pilot_id})\n"
                response += f"  Location: {pilot.location}, Status: {pilot.status}\n"
                response += f"  Skills: {', '.join(pilot.skills)}\n"
                response += f"  Certifications: {', '.join(pilot.certifications)}\n\n"
            return response
        else:
            return f"No pilots found with {target_skill} skills."
    
    def get_pilots_by_location(self, query: str) -> str:
        """Get pilots in specific location"""
        pilots = self.sheets_service.get_pilots()
        
        locations = ["bangalore", "mumbai", "delhi", "chennai"]
        target_location = None
        
        for location in locations:
            if location in query.lower():
                target_location = location
                break
        
        if not target_location:
            # Try to get location from query words
            words = query.lower().split()
            for word in words:
                if word.capitalize() in [p.location for p in pilots]:
                    target_location = word.capitalize()
                    break
        
        if not target_location:
            return "Please specify a location (e.g., 'pilots in Bangalore')."
        
        matching_pilots = [
            p for p in pilots 
            if p.location.lower() == target_location.lower()
        ]
        
        if matching_pilots:
            response = f"**Pilots in {target_location.title()}:**\n\n"
            for pilot in matching_pilots:
                response += f"- {pilot.name} ({pilot.pilot_id}) - {pilot.status}\n"
            return response
        else:
            return f"No pilots found in {target_location}."
    
    def get_pilots_by_certification(self, query: str) -> str:
        """Get pilots with specific certifications"""
        pilots = self.sheets_service.get_pilots()
        
        certs_keywords = ["dgca", "night ops", "bvlos"]
        target_cert = None
        
        for cert in certs_keywords:
            if cert in query.lower():
                target_cert = cert
                break
        
        if not target_cert:
            return "Please specify a certification to search for (e.g., 'pilots with DGCA certification')."
        
        matching_pilots = [
            p for p in pilots 
            if target_cert in [c.lower() for c in p.certifications]
        ]
        
        if matching_pilots:
            response = f"**Pilots with {target_cert.upper()} certification:**\n\n"
            for pilot in matching_pilots:
                response += f"- {pilot.name} ({pilot.pilot_id})\n"
                response += f"  Status: {pilot.status}, Location: {pilot.location}\n\n"
            return response
        else:
            return f"No pilots found with {target_cert.upper()} certification."
    
    def get_roster_summary(self) -> str:
        """Get overall roster summary"""
        pilots = self.sheets_service.get_pilots()
        
        response = "**Pilot Roster Summary**\n\n"
        
        # Group by status
        status_groups = {}
        for pilot in pilots:
            status_groups.setdefault(pilot.status, []).append(pilot)
        
        for status, pilots_list in status_groups.items():
            response += f"**{status} ({len(pilots_list)})**\n"
            for pilot in pilots_list[:3]:  # Show first 3 in each category
                response += f"- {pilot.name} ({pilot.pilot_id}) - {pilot.location}\n"
            if len(pilots_list) > 3:
                response += f"... and {len(pilots_list) - 3} more\n"
            response += "\n"
        
        return response
    
    def update_pilot_status(self, pilot_id: str, status: str) -> bool:
        """Update pilot status"""
        return self.sheets_service.update_pilot_status(pilot_id, status)