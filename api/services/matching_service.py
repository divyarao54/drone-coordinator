from typing import List, Optional, Tuple
from datetime import datetime, date
import logging

from api.models.pilot import Pilot
from api.models.drone import Drone
from api.models.mission import Mission

logger = logging.getLogger(__name__)

class MatchingService:
    """Service for matching pilots and drones to missions"""
    
    def find_matching_pilots(self, mission: Mission, pilots: List[Pilot] = None) -> List[Pilot]:
        """Find pilots that match mission requirements"""
        if pilots is None:
            # This should be injected by the calling service
            return []
        
        matching_pilots = []
        
        for pilot in pilots:
            # Check basic availability
            if pilot.status != "Available":
                continue
            
            # Check location
            if pilot.location != mission.location:
                continue
            
            # Check if pilot is available during mission dates
            if pilot.available_from:
                if pilot.available_from > mission.start_date:
                    continue
            
            # Check skills
            mission_skills = set(mission.required_skills)
            pilot_skills = set(pilot.skills)
            if not mission_skills.issubset(pilot_skills):
                continue
            
            # Check certifications
            mission_certs = set(mission.required_certs)
            pilot_certs = set(pilot.certifications)
            if not mission_certs.issubset(pilot_certs):
                continue
            
            # Calculate match score
            match_score = self._calculate_pilot_match_score(pilot, mission)
            matching_pilots.append((pilot, match_score))
        
        # Sort by match score (highest first)
        matching_pilots.sort(key=lambda x: x[1], reverse=True)
        return [pilot for pilot, _ in matching_pilots]
    
    def find_matching_drones(self, mission: Mission, drones: List[Drone] = None) -> List[Drone]:
        """Find drones that match mission requirements"""
        if drones is None:
            return []
        
        matching_drones = []
        
        for drone in drones:
            # Check availability
            if drone.status != "Available":
                continue
            
            # Check location
            if drone.location != mission.location:
                continue
            
            # Check maintenance status
            if drone.maintenance_due:
                if drone.maintenance_due <= mission.end_date:
                    continue
            
            # For now, accept all drones in same location
            # In real implementation, check capabilities match mission requirements
            
            matching_drones.append(drone)
        
        return matching_drones
    
    def find_best_assignment(self, mission: Mission, 
                           pilots: List[Pilot], 
                           drones: List[Drone]) -> Tuple[Optional[Pilot], Optional[Drone]]:
        """Find the best pilot-drone combination for a mission"""
        matching_pilots = self.find_matching_pilots(mission, pilots)
        matching_drones = self.find_matching_drones(mission, drones)
        
        if not matching_pilots or not matching_drones:
            return None, None
        
        # For now, return the first matching pilot and drone
        # In a real system, implement more sophisticated matching logic
        best_pilot = matching_pilots[0]
        best_drone = matching_drones[0]
        
        return best_pilot, best_drone
    
    def _calculate_pilot_match_score(self, pilot: Pilot, mission: Mission) -> float:
        """Calculate match score between pilot and mission"""
        score = 0.0
        
        # Skills match (40%)
        mission_skills = set(mission.required_skills)
        pilot_skills = set(pilot.skills)
        skill_overlap = len(mission_skills.intersection(pilot_skills))
        skill_score = (skill_overlap / len(mission_skills)) * 0.4
        score += skill_score
        
        # Certifications match (30%)
        mission_certs = set(mission.required_certs)
        pilot_certs = set(pilot.certifications)
        cert_overlap = len(mission_certs.intersection(pilot_certs))
        cert_score = (cert_overlap / len(mission_certs)) * 0.3 if mission_certs else 0.3
        score += cert_score
        
        # Location match (15%)
        if pilot.location == mission.location:
            score += 0.15
        
        # Availability timing (15%)
        if pilot.available_from:
            days_until_available = (mission.start_date - pilot.available_from).days
            if days_until_available >= 0:
                # Available on time or earlier
                if days_until_available <= 3:
                    score += 0.15
                else:
                    # Available but with some gap
                    score += 0.10
        
        return round(score, 2)
    
    def check_urgent_reassignment(self, urgent_mission: Mission, 
                                existing_assignments: dict) -> List[dict]:
        """Find options for urgent reassignment"""
        reassignment_options = []
        
        # This would implement logic for urgent reassignments
        # 1. Check if any current assignments can be preempted
        # 2. Find alternative resources for displaced assignments
        # 3. Calculate impact of reassignment
        
        return reassignment_options