from typing import List, Dict, Any
import logging
from datetime import datetime, date

from api.services.sheets_service import SheetsService
from api.models.drone import Drone

logger = logging.getLogger(__name__)

class InventoryManager:
    """Agent for managing drone inventory"""
    
    def __init__(self, sheets_service: SheetsService):
        self.sheets_service = sheets_service
    
    def handle_query(self, query: str) -> str:
        """Handle inventory-related queries"""
        drones = self.sheets_service.get_drones()
        
        if "available" in query.lower():
            return self.get_availability_report(query)
        elif "maintenance" in query.lower():
            return self.get_maintenance_report()
        elif "capability" in query.lower() or "thermal" in query.lower() or "lidar" in query.lower():
            return self.get_drones_by_capability(query)
        elif "location" in query.lower():
            return self.get_drones_by_location(query)
        else:
            return self.get_inventory_summary()
    
    def get_availability_report(self, query: str = "") -> str:
        """Get drone availability report"""
        drones = self.sheets_service.get_drones()
        
        available_drones = [d for d in drones if d.status == "Available"]
        in_use_drones = [d for d in drones if d.status == "In Use"]
        maintenance_drones = [d for d in drones if d.status == "Maintenance"]
        
        response = f"**Drone Availability Report**\n\n"
        response += f"Total Drones: {len(drones)}\n"
        response += f"Available: {len(available_drones)}\n"
        response += f"In Use: {len(in_use_drones)}\n"
        response += f"Maintenance: {len(maintenance_drones)}\n\n"
        
        if available_drones:
            response += "**Available Drones:**\n"
            for drone in available_drones:
                response += f"- {drone.drone_id} ({drone.model}) - {drone.location}\n"
                response += f"  Capabilities: {', '.join(drone.capabilities)}\n"
        
        return response
    
    def get_maintenance_report(self) -> str:
        """Get maintenance report"""
        drones = self.sheets_service.get_drones()
        today = datetime.now().date()
        
        maintenance_due = []
        maintenance_overdue = []
        
        for drone in drones:
            if drone.maintenance_due:
                days_until = (drone.maintenance_due - today).days
                
                if days_until <= 0:
                    maintenance_overdue.append((drone, abs(days_until)))
                elif days_until <= 7:
                    maintenance_due.append((drone, days_until))
        
        response = "**Maintenance Report**\n\n"
        
        if maintenance_overdue:
            response += "**⚠️ OVERDUE MAINTENANCE ⚠️**\n"
            for drone, days_overdue in maintenance_overdue:
                response += f"- {drone.drone_id} ({drone.model}) is {days_overdue} days overdue!\n"
                response += f"  Location: {drone.location}, Status: {drone.status}\n"
            response += "\n"
        
        if maintenance_due:
            response += "**⚠️ UPCOMING MAINTENANCE (within 7 days)**\n"
            for drone, days_until in maintenance_due:
                response += f"- {drone.drone_id} ({drone.model}) due in {days_until} days\n"
                response += f"  Due: {drone.maintenance_due}, Location: {drone.location}\n"
            response += "\n"
        
        if not maintenance_overdue and not maintenance_due:
            response += "No drones require immediate maintenance.\n"
        
        # Show all maintenance schedule
        response += "\n**All Maintenance Schedule:**\n"
        drones_with_maintenance = [d for d in drones if d.maintenance_due]
        drones_with_maintenance.sort(key=lambda x: x.maintenance_due)
        
        for drone in drones_with_maintenance:
            days_until = (drone.maintenance_due - today).days
            status_icon = "⚠️" if days_until <= 7 else "✅"
            response += f"{status_icon} {drone.drone_id}: {drone.maintenance_due} ({days_until} days)\n"
        
        return response
    
    def get_drones_by_capability(self, query: str) -> str:
        """Get drones with specific capabilities"""
        drones = self.sheets_service.get_drones()
        
        capabilities_keywords = ["thermal", "lidar", "rgb", "multispectral"]
        target_capability = None
        
        for capability in capabilities_keywords:
            if capability in query.lower():
                target_capability = capability
                break
        
        if not target_capability:
            return "Please specify a capability to search for (e.g., 'drones with thermal capability')."
        
        matching_drones = [
            d for d in drones 
            if target_capability in [c.lower() for c in d.capabilities]
        ]
        
        if matching_drones:
            response = f"**Drones with {target_capability.upper()} capability:**\n\n"
            for drone in matching_drones:
                response += f"- {drone.drone_id} ({drone.model})\n"
                response += f"  Status: {drone.status}, Location: {drone.location}\n"
                response += f"  All Capabilities: {', '.join(drone.capabilities)}\n"
                if drone.maintenance_due:
                    days_until = (drone.maintenance_due - datetime.now().date()).days
                    if days_until <= 7:
                        response += f"  ⚠️ Maintenance due in {days_until} days\n"
                response += "\n"
            return response
        else:
            return f"No drones found with {target_capability} capability."
    
    def get_drones_by_location(self, query: str) -> str:
        """Get drones in specific location"""
        drones = self.sheets_service.get_drones()
        
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
                if word.capitalize() in [d.location for d in drones]:
                    target_location = word.capitalize()
                    break
        
        if not target_location:
            return "Please specify a location (e.g., 'drones in Bangalore')."
        
        matching_drones = [
            d for d in drones 
            if d.location.lower() == target_location.lower()
        ]
        
        if matching_drones:
            response = f"**Drones in {target_location.title()}:**\n\n"
            
            # Group by status
            status_groups = {}
            for drone in matching_drones:
                status_groups.setdefault(drone.status, []).append(drone)
            
            for status, drones_list in status_groups.items():
                response += f"**{status}:**\n"
                for drone in drones_list:
                    response += f"- {drone.drone_id} ({drone.model})\n"
                    response += f"  Capabilities: {', '.join(drone.capabilities)}\n"
                    if drone.maintenance_due:
                        days_until = (drone.maintenance_due - datetime.now().date()).days
                        response += f"  Maintenance: {drone.maintenance_due} ({days_until} days)\n"
                response += "\n"
            
            return response
        else:
            return f"No drones found in {target_location}."
    
    def get_inventory_summary(self) -> str:
        """Get overall inventory summary"""
        drones = self.sheets_service.get_drones()
        
        response = "**Drone Inventory Summary**\n\n"
        
        # Group by model
        model_groups = {}
        for drone in drones:
            model_groups.setdefault(drone.model, []).append(drone)
        
        for model, drones_list in model_groups.items():
            response += f"**{model} ({len(drones_list)})**\n"
            
            # Count by status within model
            status_counts = {}
            for drone in drones_list:
                status_counts[drone.status] = status_counts.get(drone.status, 0) + 1
            
            for status, count in status_counts.items():
                response += f"  {status}: {count}\n"
            
            response += "\n"
        
        # Capability summary
        all_capabilities = set()
        for drone in drones:
            all_capabilities.update(drone.capabilities)
        
        response += "**Capabilities Available:**\n"
        for capability in sorted(all_capabilities):
            count = sum(1 for d in drones if capability in d.capabilities)
            response += f"- {capability}: {count} drones\n"
        
        return response
    
    def update_drone_status(self, drone_id: str, status: str) -> bool:
        """Update drone status"""
        return self.sheets_service.update_drone_status(drone_id, status)