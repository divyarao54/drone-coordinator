from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from api.services.sheets_service import SheetsService
from api.services.matching_service import MatchingService
from api.agents.roster_manager import RosterManager
from api.agents.inventory_manager import InventoryManager
from api.agents.assignment_tracker import AssignmentTracker
from api.agents.conflict_detector import ConflictDetector

# Import models for type hints
from api.models.mission import Mission
from api.models.pilot import Pilot
from api.models.drone import Drone

logger = logging.getLogger(__name__)

class CoordinatorAgent:
    """Main coordinator agent that orchestrates all operations"""
    
    def __init__(self, sheets_service: SheetsService, matching_service: MatchingService):
        self.sheets_service = sheets_service
        self.matching_service = matching_service
        
        # Initialize specialized agents
        self.roster_manager = RosterManager(sheets_service)
        self.inventory_manager = InventoryManager(sheets_service)
        self.assignment_tracker = AssignmentTracker(sheets_service, matching_service)
        self.conflict_detector = ConflictDetector(sheets_service)
        
        # Conversation context
        self.conversation_context = []
        
    def process_query(self, user_input: str) -> str:
        """Process user query and return appropriate response"""
        try:
            # Store conversation context
            self.conversation_context.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })
            
            # Parse user intent
            intent = self._parse_intent(user_input)
            
            # Route to appropriate handler
            response = self._route_to_handler(intent, user_input)
            
            # Store assistant response
            self.conversation_context.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return "I encountered an error processing your request. Please try again."
    
    def assign_mission(self, project_id: str, pilot_id: str, drone_id: str) -> Dict[str, Any]:
        """Assign pilot and drone to a mission"""
        try:
            # Get mission, pilot, and drone
            mission = self.sheets_service.get_mission(project_id)
            pilot = self.sheets_service.get_pilot(pilot_id)
            drone = self.sheets_service.get_drone(drone_id)
            
            if not mission:
                return {"success": False, "error": f"Mission {project_id} not found"}
            if not pilot:
                return {"success": False, "error": f"Pilot {pilot_id} not found"}
            if not drone:
                return {"success": False, "error": f"Drone {drone_id} not found"}
            
            # Check for conflicts
            conflicts = self.conflict_detector.check_assignment_conflicts(
                mission, pilot, drone
            )
            
            if conflicts:
                conflict_messages = "\n".join([c["message"] for c in conflicts])
                return {
                    "success": False, 
                    "error": f"Assignment conflicts detected:\n{conflict_messages}"
                }
            
            # Perform assignment
            success = self.sheets_service.assign_to_mission(project_id, pilot_id, drone_id)
            
            if success:
                return {
                    "success": True,
                    "assignment": {
                        "project_id": project_id,
                        "pilot_id": pilot_id,
                        "drone_id": drone_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                return {"success": False, "error": "Failed to update assignment in sheets"}
                
        except Exception as e:
            logger.error(f"Error assigning mission: {e}")
            return {"success": False, "error": str(e)}
    
    def handle_urgent_reassignment(self, urgent_mission_id: str) -> Dict[str, Any]:
        """Handle urgent reassignment for a mission"""
        try:
            urgent_mission = self.sheets_service.get_mission(urgent_mission_id)
            if not urgent_mission:
                return {"success": False, "error": "Urgent mission not found"}
            
            # Get all current assignments
            missions = self.sheets_service.get_missions()
            pilots = self.sheets_service.get_pilots()
            drones = self.sheets_service.get_drones()
            
            # Find resources that can be reassigned
            available_pilots = self.matching_service.find_matching_pilots(urgent_mission, pilots)
            available_drones = self.matching_service.find_matching_drones(urgent_mission, drones)
            
            if not available_pilots or not available_drones:
                # Try to find resources that could be reassigned from lower priority missions
                return self._find_reassignment_options(urgent_mission, missions, pilots, drones)
            
            # Assign available resources
            best_pilot = available_pilots[0]
            best_drone = available_drones[0]
            
            result = self.assign_mission(
                urgent_mission_id, 
                best_pilot.pilot_id, 
                best_drone.drone_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling urgent reassignment: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_intent(self, user_input: str) -> str:
        """Parse user intent from input"""
        user_input = user_input.lower()
        
        # Roster management intents
        if any(word in user_input for word in ['pilot', 'roster', 'availability']):
            if 'status' in user_input or 'update' in user_input:
                return 'update_pilot_status'
            elif 'available' in user_input:
                return 'check_pilot_availability'
            else:
                return 'roster_query'
        
        # Drone inventory intents
        elif any(word in user_input for word in ['drone', 'fleet', 'inventory']):
            if 'maintenance' in user_input:
                return 'check_maintenance'
            elif 'available' in user_input:
                return 'check_drone_availability'
            else:
                return 'drone_query'
        
        # Assignment intents
        elif any(word in user_input for word in ['assign', 'mission', 'project']):
            if 'urgent' in user_input or 'emergency' in user_input:
                return 'urgent_assignment'
            else:
                return 'assignment_query'
        
        # Conflict detection intents
        elif any(word in user_input for word in ['conflict', 'problem', 'issue', 'warning']):
            return 'check_conflicts'
        
        # General help
        elif any(word in user_input for word in ['help', 'what can', 'how to']):
            return 'help'
        
        # Default to general conversation
        else:
            return 'general_query'
    
    def _route_to_handler(self, intent: str, user_input: str) -> str:
        """Route query to appropriate handler"""
        if intent == 'update_pilot_status':
            return self._handle_pilot_status_update(user_input)
        elif intent == 'check_pilot_availability':
            return self.roster_manager.get_availability_report(user_input)
        elif intent == 'roster_query':
            return self.roster_manager.handle_query(user_input)
        elif intent == 'check_maintenance':
            return self.inventory_manager.get_maintenance_report()
        elif intent == 'check_drone_availability':
            return self.inventory_manager.get_availability_report(user_input)
        elif intent == 'drone_query':
            return self.inventory_manager.handle_query(user_input)
        elif intent == 'urgent_assignment':
            return self._handle_urgent_assignment(user_input)
        elif intent == 'assignment_query':
            return self.assignment_tracker.handle_query(user_input)
        elif intent == 'check_conflicts':
            conflicts = self.conflict_detector.detect_all_conflicts()
            if conflicts:
                return "I found the following conflicts:\n" + "\n".join([c["message"] for c in conflicts])
            else:
                return "No conflicts detected in the system."
        elif intent == 'help':
            return self._get_help_message()
        else:
            return self._handle_general_query(user_input)
    
    def _handle_pilot_status_update(self, user_input: str) -> str:
        """Handle pilot status update requests"""
        # Extract pilot ID and status from user input
        # This is a simplified version - in reality, you'd use NLP
        pilots = self.sheets_service.get_pilots()
        
        # Look for pilot names/IDs in input
        for pilot in pilots:
            if pilot.name.lower() in user_input.lower() or pilot.pilot_id.lower() in user_input.lower():
                # Extract status from input
                status_keywords = {
                    'available': 'Available',
                    'on leave': 'On Leave',
                    'unavailable': 'Unavailable',
                    'assigned': 'Assigned'
                }
                
                for keyword, status in status_keywords.items():
                    if keyword in user_input.lower():
                        success = self.sheets_service.update_pilot_status(pilot.pilot_id, status)
                        if success:
                            return f"Updated {pilot.name} ({pilot.pilot_id}) status to {status}."
                        else:
                            return f"Failed to update {pilot.name}'s status."
        
        return "I couldn't identify which pilot's status to update. Please specify the pilot name or ID."
    
    def _handle_urgent_assignment(self, user_input: str) -> str:
        """Handle urgent assignment requests"""
        # Extract mission ID from input
        missions = self.sheets_service.get_missions()
        
        for mission in missions:
            if mission.project_id.lower() in user_input.lower() or mission.client.lower() in user_input.lower():
                result = self.handle_urgent_reassignment(mission.project_id)
                if result["success"]:
                    return f"Urgent assignment completed for {mission.project_id}."
                else:
                    return f"Failed to assign urgently: {result['error']}"
        
        return "I couldn't identify which mission needs urgent assignment. Please specify the project ID or client name."
    
    def _handle_general_query(self, user_input: str) -> str:
        """Handle general queries"""
        # This could be enhanced with an LLM for natural conversation
        general_responses = {
            "hello": "Hello! I'm your Drone Operations Coordinator. How can I help you today?",
            "hi": "Hi there! I'm here to help manage drone operations. What do you need?",
            "thanks": "You're welcome! Let me know if you need anything else.",
            "bye": "Goodbye! Have a great day.",
        }
        
        user_input_lower = user_input.lower()
        for keyword, response in general_responses.items():
            if keyword in user_input_lower:
                return response
        
        # Default response for unrecognized queries
        return "I'm not sure I understand. You can ask me about:\n" \
               "- Pilot availability and status\n" \
               "- Drone inventory and maintenance\n" \
               "- Mission assignments\n" \
               "- Conflict detection\n" \
               "Or type 'help' for more options."
    
    def _get_help_message(self) -> str:
        """Get help message"""
        return """I can help you with the following:

**Roster Management:**
- Check pilot availability by skill, location, or certification
- Update pilot status (Available/On Leave/Unavailable)
- View current pilot assignments

**Drone Inventory:**
- Check drone availability by capability or location
- View maintenance schedules
- Update drone status

**Assignment Tracking:**
- Find matching pilots and drones for missions
- Make new assignments
- Handle urgent reassignments

**Conflict Detection:**
- Check for scheduling conflicts
- Detect skill/certification mismatches
- Find location mismatches

**Examples:**
- "Show me available pilots in Bangalore"
- "Update Arjun's status to On Leave"
- "Find drones available for thermal inspection"
- "Check for conflicts in assignments"
- "Urgently assign resources to PRJ002"

What would you like to do?"""
    
    def _find_reassignment_options(self, urgent_mission: Mission, 
                                 all_missions: List[Mission],
                                 all_pilots: List[Pilot],
                                 all_drones: List[Drone]) -> Dict[str, Any]:
        """Find reassignment options for urgent mission"""
        # This implements cascading reassignment logic
        options = []
        
        # Find lower priority missions that could be delayed
        lower_priority_missions = [
            m for m in all_missions 
            if m.priority in ['Standard', 'Low'] 
            and m.assigned_pilot and m.assigned_drone
        ]
        
        for mission in lower_priority_missions:
            # Check if resources from this mission could serve the urgent mission
            pilot = next((p for p in all_pilots if p.pilot_id == mission.assigned_pilot), None)
            drone = next((d for d in all_drones if d.drone_id == mission.assigned_drone), None)
            
            if pilot and drone:
                # Check if they match urgent mission requirements
                matching_pilots = self.matching_service.find_matching_pilots(urgent_mission, [pilot])
                matching_drones = self.matching_service.find_matching_drones(urgent_mission, [drone])
                
                if matching_pilots and matching_drones:
                    options.append({
                        "mission_to_delay": mission.project_id,
                        "pilot": pilot.pilot_id,
                        "drone": drone.drone_id,
                        "priority_difference": self._get_priority_difference(urgent_mission.priority, mission.priority)
                    })
        
        if options:
            # Sort by least disruptive option
            options.sort(key=lambda x: x["priority_difference"], reverse=True)
            
            return {
                "success": True,
                "reassignment_options": options,
                "message": f"Found {len(options)} reassignment options"
            }
        else:
            return {
                "success": False,
                "error": "No reassignment options found"
            }
    
    def _get_priority_difference(self, priority1: str, priority2: str) -> int:
        """Calculate priority difference"""
        priority_levels = {
            "Urgent": 4,
            "High": 3,
            "Standard": 2,
            "Low": 1
        }
        
        return priority_levels.get(priority1, 0) - priority_levels.get(priority2, 0)