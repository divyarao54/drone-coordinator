from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, date

from api.services.sheets_service import SheetsService
from api.models.pilot import Pilot
from api.models.drone import Drone
from api.models.mission import Mission

logger = logging.getLogger(__name__)

class ConflictDetector:
    """Agent for detecting conflicts in assignments"""
    
    def __init__(self, sheets_service: SheetsService):
        self.sheets_service = sheets_service
    
    def detect_all_conflicts(self) -> List[Dict[str, Any]]:
        """Detect all conflicts in the system"""
        conflicts = []
        
        # Get all data
        missions = self.sheets_service.get_missions()
        pilots = self.sheets_service.get_pilots()
        drones = self.sheets_service.get_drones()
        
        # Check each mission for conflicts
        for mission in missions:
            if mission.assigned_pilot and mission.assigned_drone:
                # Check assignment conflicts
                mission_conflicts = self.check_assignment_conflicts(
                    mission, 
                    next((p for p in pilots if p.pilot_id == mission.assigned_pilot), None),
                    next((d for d in drones if d.drone_id == mission.assigned_drone), None)
                )
                conflicts.extend(mission_conflicts)
        
        # Check for double bookings
        conflicts.extend(self.check_double_bookings(missions, pilots, drones))
        
        # Check for maintenance conflicts
        conflicts.extend(self.check_maintenance_conflicts(drones, missions))
        
        # Check for certification conflicts
        conflicts.extend(self.check_certification_conflicts(missions, pilots))
        
        # Check for location mismatches
        conflicts.extend(self.check_location_mismatches(missions, pilots, drones))
        
        return conflicts
    
    def check_assignment_conflicts(self, mission: Mission, pilot: Pilot, drone: Drone) -> List[Dict[str, Any]]:
        """Check conflicts for a specific assignment"""
        conflicts = []
        
        if not pilot or not drone:
            return conflicts
        
        # 1. Check if pilot has required skills
        mission_skills = set(mission.required_skills)
        pilot_skills = set(pilot.skills)
        missing_skills = mission_skills - pilot_skills
        
        if missing_skills:
            conflicts.append({
                "type": "skill_mismatch",
                "severity": "high",
                "message": f"Pilot {pilot.name} ({pilot.pilot_id}) lacks required skills: {', '.join(missing_skills)} for mission {mission.project_id}"
            })
        
        # 2. Check if pilot has required certifications
        mission_certs = set(mission.required_certs)
        pilot_certs = set(pilot.certifications)
        missing_certs = mission_certs - pilot_certs
        
        if missing_certs:
            conflicts.append({
                "type": "certification_mismatch",
                "severity": "high",
                "message": f"Pilot {pilot.name} lacks required certifications: {', '.join(missing_certs)} for mission {mission.project_id}"
            })
        
        # 3. Check location mismatch
        if pilot.location != mission.location:
            conflicts.append({
                "type": "location_mismatch",
                "severity": "medium",
                "message": f"Pilot {pilot.name} is in {pilot.location}, but mission {mission.project_id} is in {mission.location}"
            })
        
        if drone.location != mission.location:
            conflicts.append({
                "type": "location_mismatch",
                "severity": "medium",
                "message": f"Drone {drone.drone_id} is in {drone.location}, but mission {mission.project_id} is in {mission.location}"
            })
        
        # 4. Check drone maintenance
        if drone.maintenance_due and drone.maintenance_due <= mission.end_date:
            conflicts.append({
                "type": "maintenance_conflict",
                "severity": "high",
                "message": f"Drone {drone.drone_id} requires maintenance on {drone.maintenance_due}, during mission {mission.project_id}"
            })
        
        # 5. Check pilot availability
        if pilot.available_from and pilot.available_from > mission.start_date:
            conflicts.append({
                "type": "availability_conflict",
                "severity": "high",
                "message": f"Pilot {pilot.name} is only available from {pilot.available_from}, but mission {mission.project_id} starts on {mission.start_date}"
            })
        
        return conflicts
    
    def check_double_bookings(self, missions: List[Mission], pilots: List[Pilot], drones: List[Drone]) -> List[Dict[str, Any]]:
        """Check for double bookings of pilots and drones"""
        conflicts = []
        
        # Check pilot double bookings
        pilot_assignments = {}
        for mission in missions:
            if mission.assigned_pilot:
                pilot_assignments.setdefault(mission.assigned_pilot, []).append(mission)
        
        for pilot_id, assigned_missions in pilot_assignments.items():
            if len(assigned_missions) > 1:
                # Check for overlapping dates
                for i in range(len(assigned_missions)):
                    for j in range(i + 1, len(assigned_missions)):
                        m1 = assigned_missions[i]
                        m2 = assigned_missions[j]
                        
                        if self._dates_overlap(m1.start_date, m1.end_date, m2.start_date, m2.end_date):
                            pilot = next((p for p in pilots if p.pilot_id == pilot_id), None)
                            pilot_name = pilot.name if pilot else pilot_id
                            
                            conflicts.append({
                                "type": "double_booking",
                                "severity": "critical",
                                "message": f"Pilot {pilot_name} double-booked on overlapping missions: {m1.project_id} ({m1.start_date}-{m1.end_date}) and {m2.project_id} ({m2.start_date}-{m2.end_date})"
                            })
        
        # Check drone double bookings
        drone_assignments = {}
        for mission in missions:
            if mission.assigned_drone:
                drone_assignments.setdefault(mission.assigned_drone, []).append(mission)
        
        for drone_id, assigned_missions in drone_assignments.items():
            if len(assigned_missions) > 1:
                for i in range(len(assigned_missions)):
                    for j in range(i + 1, len(assigned_missions)):
                        m1 = assigned_missions[i]
                        m2 = assigned_missions[j]
                        
                        if self._dates_overlap(m1.start_date, m1.end_date, m2.start_date, m2.end_date):
                            conflicts.append({
                                "type": "double_booking",
                                "severity": "critical",
                                "message": f"Drone {drone_id} double-booked on overlapping missions: {m1.project_id} and {m2.project_id}"
                            })
        
        return conflicts
    
    def check_maintenance_conflicts(self, drones: List[Drone], missions: List[Mission]) -> List[Dict[str, Any]]:
        """Check for maintenance conflicts"""
        conflicts = []
        today = datetime.now().date()
        
        for drone in drones:
            if drone.maintenance_due:
                # Check if drone is assigned during maintenance period
                for mission in missions:
                    if mission.assigned_drone == drone.drone_id:
                        if drone.maintenance_due <= mission.end_date:
                            days_until = (drone.maintenance_due - today).days
                            status = "OVERDUE" if days_until < 0 else f"due in {days_until} days"
                            
                            conflicts.append({
                                "type": "maintenance_conflict",
                                "severity": "high",
                                "message": f"Drone {drone.drone_id} assigned to {mission.project_id} during maintenance period (maintenance {status}: {drone.maintenance_due})"
                            })
        
        return conflicts
    
    def check_certification_conflicts(self, missions: List[Mission], pilots: List[Pilot]) -> List[Dict[str, Any]]:
        """Check for certification conflicts"""
        conflicts = []
        
        for mission in missions:
            if mission.assigned_pilot:
                pilot = next((p for p in pilots if p.pilot_id == mission.assigned_pilot), None)
                if pilot:
                    mission_certs = set(mission.required_certs)
                    pilot_certs = set(pilot.certifications)
                    missing_certs = mission_certs - pilot_certs
                    
                    if missing_certs:
                        conflicts.append({
                            "type": "certification_mismatch",
                            "severity": "high",
                            "message": f"Pilot {pilot.name} assigned to {mission.project_id} lacks certifications: {', '.join(missing_certs)}"
                        })
        
        return conflicts
    
    def check_location_mismatches(self, missions: List[Mission], pilots: List[Pilot], drones: List[Drone]) -> List[Dict[str, Any]]:
        """Check for location mismatches"""
        conflicts = []
        
        for mission in missions:
            if mission.assigned_pilot:
                pilot = next((p for p in pilots if p.pilot_id == mission.assigned_pilot), None)
                if pilot and pilot.location != mission.location:
                    conflicts.append({
                        "type": "location_mismatch",
                        "severity": "medium",
                        "message": f"Pilot {pilot.name} in {pilot.location} assigned to mission in {mission.location} ({mission.project_id})"
                    })
            
            if mission.assigned_drone:
                drone = next((d for d in drones if d.drone_id == mission.assigned_drone), None)
                if drone and drone.location != mission.location:
                    conflicts.append({
                        "type": "location_mismatch",
                        "severity": "medium",
                        "message": f"Drone {drone.drone_id} in {drone.location} assigned to mission in {mission.location} ({mission.project_id})"
                    })
        
        return conflicts
    
    def check_pilot_conflicts(self, pilot_id: str) -> List[Dict[str, Any]]:
        """Check conflicts for a specific pilot"""
        conflicts = []
        
        pilot = self.sheets_service.get_pilot(pilot_id)
        if not pilot:
            return conflicts
        
        missions = self.sheets_service.get_missions()
        
        # Find missions assigned to this pilot
        assigned_missions = [m for m in missions if m.assigned_pilot == pilot_id]
        
        if len(assigned_missions) > 1:
            # Check for overlapping dates
            for i in range(len(assigned_missions)):
                for j in range(i + 1, len(assigned_missions)):
                    m1 = assigned_missions[i]
                    m2 = assigned_missions[j]
                    
                    if self._dates_overlap(m1.start_date, m1.end_date, m2.start_date, m2.end_date):
                        conflicts.append({
                            "type": "double_booking",
                            "severity": "critical",
                            "message": f"Pilot {pilot.name} has overlapping assignments: {m1.project_id} and {m2.project_id}"
                        })
        
        return conflicts
    
    def _dates_overlap(self, start1: date, end1: date, start2: date, end2: date) -> bool:
        """Check if two date ranges overlap"""
        return start1 <= end2 and start2 <= end1