from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime
import re

from api.models.pilot import Pilot
from api.models.drone import Drone
from api.models.mission import Mission

def validate_pilot_data(pilot_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate pilot data"""
    errors = []
    
    # Required fields
    required_fields = ['pilot_id', 'name', 'skills', 'certifications', 'location', 'status']
    for field in required_fields:
        if field not in pilot_data or not pilot_data[field]:
            errors.append(f"Missing required field: {field}")
    
    # Pilot ID format
    if 'pilot_id' in pilot_data:
        if not re.match(r'^P\d{3}$', str(pilot_data['pilot_id'])):
            errors.append("Pilot ID must be in format PXXX (e.g., P001)")
    
    # Status validation
    if 'status' in pilot_data:
        valid_statuses = ['Available', 'Assigned', 'On Leave', 'Unavailable']
        if pilot_data['status'] not in valid_statuses:
            errors.append(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    # Skills and certifications should be lists or comma-separated strings
    for field in ['skills', 'certifications']:
        if field in pilot_data:
            value = pilot_data[field]
            if isinstance(value, str):
                # Convert to list for validation
                items = [item.strip() for item in value.split(',') if item.strip()]
                if not items:
                    errors.append(f"{field} cannot be empty")
            elif isinstance(value, list):
                if not value:
                    errors.append(f"{field} cannot be empty list")
            else:
                errors.append(f"{field} must be a string or list")
    
    return len(errors) == 0, errors

def validate_drone_data(drone_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate drone data"""
    errors = []
    
    # Required fields
    required_fields = ['drone_id', 'model', 'capabilities', 'status', 'location']
    for field in required_fields:
        if field not in drone_data or not drone_data[field]:
            errors.append(f"Missing required field: {field}")
    
    # Drone ID format
    if 'drone_id' in drone_data:
        if not re.match(r'^D\d{3}$', str(drone_data['drone_id'])):
            errors.append("Drone ID must be in format DXXX (e.g., D001)")
    
    # Status validation
    if 'status' in drone_data:
        valid_statuses = ['Available', 'In Use', 'Maintenance', 'Unavailable']
        if drone_data['status'] not in valid_statuses:
            errors.append(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    # Capabilities validation
    if 'capabilities' in drone_data:
        value = drone_data['capabilities']
        if isinstance(value, str):
            items = [item.strip() for item in value.split(',') if item.strip()]
            if not items:
                errors.append("capabilities cannot be empty")
        elif isinstance(value, list):
            if not value:
                errors.append("capabilities cannot be empty list")
    
    # Maintenance date validation
    if 'maintenance_due' in drone_data and drone_data['maintenance_due']:
        try:
            maintenance_date = parse_date(drone_data['maintenance_due'])
            if maintenance_date and maintenance_date < date.today():
                errors.append("Maintenance date cannot be in the past")
        except ValueError:
            errors.append("Invalid maintenance date format")
    
    return len(errors) == 0, errors

def validate_mission_data(mission_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate mission data"""
    errors = []
    
    # Required fields
    required_fields = ['project_id', 'client', 'location', 'required_skills', 
                      'required_certs', 'start_date', 'end_date', 'priority']
    for field in required_fields:
        if field not in mission_data or not mission_data[field]:
            errors.append(f"Missing required field: {field}")
    
    # Project ID format
    if 'project_id' in mission_data:
        if not re.match(r'^PRJ\d{3}$', str(mission_data['project_id'])):
            errors.append("Project ID must be in format PRJXXX (e.g., PRJ001)")
    
    # Date validation
    if 'start_date' in mission_data and 'end_date' in mission_data:
        try:
            start_date = parse_date(mission_data['start_date'])
            end_date = parse_date(mission_data['end_date'])
            
            if start_date and end_date:
                if start_date > end_date:
                    errors.append("Start date must be before end date")
                if start_date < date.today():
                    errors.append("Start date cannot be in the past")
        except ValueError:
            errors.append("Invalid date format for start_date or end_date")
    
    # Priority validation
    if 'priority' in mission_data:
        valid_priorities = ['Urgent', 'High', 'Standard', 'Low']
        if mission_data['priority'] not in valid_priorities:
            errors.append(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
    
    # Skills and certifications validation
    for field in ['required_skills', 'required_certs']:
        if field in mission_data:
            value = mission_data[field]
            if isinstance(value, str):
                items = [item.strip() for item in value.split(',') if item.strip()]
                if not items:
                    errors.append(f"{field} cannot be empty")
            elif isinstance(value, list):
                if not value:
                    errors.append(f"{field} cannot be empty list")
    
    return len(errors) == 0, errors

def validate_assignment(project_id: str, pilot_id: str, drone_id: str, 
                       pilots: List[Pilot], drones: List[Drone], 
                       missions: List[Mission]) -> Tuple[bool, List[str]]:
    """Validate an assignment"""
    errors = []
    
    # Check if project exists
    mission = next((m for m in missions if m.project_id == project_id), None)
    if not mission:
        errors.append(f"Mission {project_id} not found")
    
    # Check if pilot exists
    pilot = next((p for p in pilots if p.pilot_id == pilot_id), None)
    if not pilot:
        errors.append(f"Pilot {pilot_id} not found")
    
    # Check if drone exists
    drone = next((d for d in drones if d.drone_id == drone_id), None)
    if not drone:
        errors.append(f"Drone {drone_id} not found")
    
    if mission and pilot and drone:
        # Check if pilot is available
        if pilot.status != "Available":
            errors.append(f"Pilot {pilot_id} is not available (status: {pilot.status})")
        
        # Check if drone is available
        if drone.status != "Available":
            errors.append(f"Drone {drone_id} is not available (status: {drone.status})")
        
        # Check location match
        if pilot.location != mission.location:
            errors.append(f"Pilot {pilot_id} is in {pilot.location}, mission is in {mission.location}")
        
        if drone.location != mission.location:
            errors.append(f"Drone {drone_id} is in {drone.location}, mission is in {mission.location}")
        
        # Check skills match
        mission_skills = set(mission.required_skills)
        pilot_skills = set(pilot.skills)
        if not mission_skills.issubset(pilot_skills):
            missing = mission_skills - pilot_skills
            errors.append(f"Pilot {pilot_id} lacks required skills: {', '.join(missing)}")
        
        # Check certifications match
        mission_certs = set(mission.required_certs)
        pilot_certs = set(pilot.certifications)
        if not mission_certs.issubset(pilot_certs):
            missing = mission_certs - pilot_certs
            errors.append(f"Pilot {pilot_id} lacks required certifications: {', '.join(missing)}")
        
        # Check drone maintenance
        if drone.maintenance_due and drone.maintenance_due <= mission.end_date:
            errors.append(f"Drone {drone_id} requires maintenance on {drone.maintenance_due}")
    
    return len(errors) == 0, errors

def parse_date(date_str: str) -> Optional[date]:
    """Parse date string to date object"""
    if not date_str:
        return None
    
    date_formats = [
        '%Y-%m-%d',  # 2026-02-06
        '%d/%m/%Y',  # 06/02/2026
        '%m/%d/%Y',  # 02/06/2026
        '%d-%m-%Y',  # 06-02-2026
    ]
    
    for date_format in date_formats:
        try:
            return datetime.strptime(str(date_str).strip(), date_format).date()
        except ValueError:
            continue
    
    return None

def validate_date_range(start_date: date, end_date: date) -> Tuple[bool, str]:
    """Validate date range"""
    if start_date > end_date:
        return False, "Start date must be before end date"
    if start_date < date.today():
        return False, "Start date cannot be in the past"
    return True, ""

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    pattern = r'^\+?1?\d{9,15}$'
    return bool(re.match(pattern, phone))

def sanitize_input(input_str: str) -> str:
    """Sanitize user input"""
    if not input_str:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', input_str)
    return sanitized.strip()

def validate_priority_order(priority1: str, priority2: str) -> bool:
    """Validate if priority1 is higher than priority2"""
    priority_order = {
        'Urgent': 4,
        'High': 3,
        'Standard': 2,
        'Low': 1
    }
    
    return priority_order.get(priority1, 0) > priority_order.get(priority2, 0)