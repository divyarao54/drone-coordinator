import gspread
from google.oauth2.service_account import Credentials
from typing import List, Optional, Dict, Any
import pandas as pd
from datetime import datetime
import os
import logging

from api.models.pilot import Pilot
from api.models.drone import Drone
from api.models.mission import Mission

logger = logging.getLogger(__name__)

class SheetsService:
    """Service for Google Sheets integration"""
    
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self.credentials = None
        self.client = None
        self.sheets = {}
        
        # Local cache
        self._pilots_cache = None
        self._drones_cache = None
        self._missions_cache = None
        self._last_sync = None
        
    def authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            # Try to get credentials from environment variable
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                import json
                creds_dict = json.loads(creds_json)
                self.credentials = Credentials.from_service_account_info(
                    creds_dict, scopes=self.scopes
                )
            else:
                # Try to load from file
                creds_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'skylarkdrones-487006-99dc39e2a5ff.json')
                self.credentials = Credentials.from_service_account_file(
                    creds_file, scopes=self.scopes
                )
            
            self.client = gspread.authorize(self.credentials)
            logger.info("Google Sheets authentication successful")
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            # Fallback to local data if available
            logger.info("Falling back to local data")
    
    def _get_sheet(self, sheet_name: str, worksheet_name: str = None):
        """Get a specific sheet"""
        try:
            if sheet_name not in self.sheets:
                self.sheets[sheet_name] = self.client.open(sheet_name)
            
            sheet = self.sheets[sheet_name]
            if worksheet_name:
                return sheet.worksheet(worksheet_name)
            return sheet.sheet1
            
        except Exception as e:
            logger.error(f"Error accessing sheet {sheet_name}: {e}")
            return None
    
    def get_pilots(self) -> List[Pilot]:
        """Get all pilots from Google Sheets"""
        try:
            if self._pilots_cache and self._last_sync:
                # Return cache if recent (less than 5 minutes old)
                if (datetime.now() - self._last_sync).seconds < 300:
                    return self._pilots_cache
            
            # Try to get from Google Sheets
            worksheet = self._get_sheet("Drone Operations", "pilot_roster")
            if worksheet:
                records = worksheet.get_all_records()
                pilots = []
                
                for record in records:
                    # Parse skills and certifications from strings to lists
                    skills = [s.strip() for s in record.get('skills', '').split(',')]
                    certs = [c.strip() for c in record.get('certifications', '').split(',')]
                    
                    pilot = Pilot(
                        pilot_id=record.get('pilot_id', ''),
                        name=record.get('name', ''),
                        skills=skills,
                        certifications=certs,
                        location=record.get('location', ''),
                        status=record.get('status', 'Available'),
                        current_assignment=record.get('current_assignment', None),
                        available_from=self._parse_date(record.get('available_from', ''))
                    )
                    pilots.append(pilot)
                
                self._pilots_cache = pilots
                self._last_sync = datetime.now()
                return pilots
            
            # Fallback to local data
            return self._load_local_pilots()
            
        except Exception as e:
            logger.error(f"Error getting pilots: {e}")
            return self._load_local_pilots()
    
    def get_drones(self) -> List[Drone]:
        """Get all drones from Google Sheets"""
        try:
            if self._drones_cache and self._last_sync:
                if (datetime.now() - self._last_sync).seconds < 300:
                    return self._drones_cache
            
            worksheet = self._get_sheet("Drone Operations", "drone_fleet")
            if worksheet:
                records = worksheet.get_all_records()
                drones = []
                
                for record in records:
                    capabilities = [c.strip() for c in record.get('capabilities', '').split(',')]
                    
                    drone = Drone(
                        drone_id=record.get('drone_id', ''),
                        model=record.get('model', ''),
                        capabilities=capabilities,
                        status=record.get('status', 'Available'),
                        location=record.get('location', ''),
                        current_assignment=record.get('current_assignment', None),
                        maintenance_due=self._parse_date(record.get('maintenance_due', ''))
                    )
                    drones.append(drone)
                
                self._drones_cache = drones
                self._last_sync = datetime.now()
                return drones
            
            return self._load_local_drones()
            
        except Exception as e:
            logger.error(f"Error getting drones: {e}")
            return self._load_local_drones()
    
    def get_missions(self) -> List[Mission]:
        """Get all missions from Google Sheets"""
        try:
            if self._missions_cache and self._last_sync:
                if (datetime.now() - self._last_sync).seconds < 300:
                    return self._missions_cache
            
            worksheet = self._get_sheet("Drone Operations", "missions")
            if worksheet:
                records = worksheet.get_all_records()
                missions = []
                
                for record in records:
                    skills = [s.strip() for s in record.get('required_skills', '').split(',')]
                    certs = [c.strip() for c in record.get('required_certs', '').split(',')]
                    
                    mission = Mission(
                        project_id=record.get('project_id', ''),
                        client=record.get('client', ''),
                        location=record.get('location', ''),
                        required_skills=skills,
                        required_certs=certs,
                        start_date=self._parse_date(record.get('start_date', '')),
                        end_date=self._parse_date(record.get('end_date', '')),
                        priority=record.get('priority', 'Standard'),
                        assigned_pilot=record.get('assigned_pilot', None),
                        assigned_drone=record.get('assigned_drone', None)
                    )
                    missions.append(mission)
                
                self._missions_cache = missions
                self._last_sync = datetime.now()
                return missions
            
            return self._load_local_missions()
            
        except Exception as e:
            logger.error(f"Error getting missions: {e}")
            return self._load_local_missions()
    
    def get_pilot(self, pilot_id: str) -> Optional[Pilot]:
        """Get a specific pilot"""
        pilots = self.get_pilots()
        for pilot in pilots:
            if pilot.pilot_id == pilot_id:
                return pilot
        return None
    
    def get_drone(self, drone_id: str) -> Optional[Drone]:
        """Get a specific drone"""
        drones = self.get_drones()
        for drone in drones:
            if drone.drone_id == drone_id:
                return drone
        return None
    
    def get_mission(self, project_id: str) -> Optional[Mission]:
        """Get a specific mission"""
        missions = self.get_missions()
        for mission in missions:
            if mission.project_id == project_id:
                return mission
        return None
    
    def update_pilot_status(self, pilot_id: str, status: str) -> bool:
        """Update pilot status in Google Sheets"""
        try:
            worksheet = self._get_sheet("Drone Operations", "pilot_roster")
            if not worksheet:
                return False
            
            # Find the row with the pilot_id
            cell = worksheet.find(pilot_id)
            if not cell:
                return False
            
            # Update status in column G (status column)
            worksheet.update_cell(cell.row, 7, status)
            
            # Clear cache to force refresh
            self._pilots_cache = None
            
            # Also update local CSV
            self._update_local_pilot_status(pilot_id, status)
            
            logger.info(f"Updated pilot {pilot_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating pilot status: {e}")
            return False
    
    def update_drone_status(self, drone_id: str, status: str) -> bool:
        """Update drone status in Google Sheets"""
        try:
            worksheet = self._get_sheet("Drone Operations", "drone_fleet")
            if not worksheet:
                return False
            
            cell = worksheet.find(drone_id)
            if not cell:
                return False
            
            # Update status in column D (status column)
            worksheet.update_cell(cell.row, 4, status)
            
            self._drones_cache = None
            self._update_local_drone_status(drone_id, status)
            
            logger.info(f"Updated drone {drone_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating drone status: {e}")
            return False
    
    def assign_to_mission(self, project_id: str, pilot_id: str, drone_id: str) -> bool:
        """Assign pilot and drone to mission"""
        try:
            # Update mission sheet
            mission_worksheet = self._get_sheet("Drone Operations", "missions")
            if mission_worksheet:
                cell = mission_worksheet.find(project_id)
                if cell:
                    # Update assigned pilot and drone (assuming columns I and J)
                    mission_worksheet.update_cell(cell.row, 9, pilot_id)
                    mission_worksheet.update_cell(cell.row, 10, drone_id)
            
            # Update pilot sheet
            pilot_worksheet = self._get_sheet("Drone Operations", "pilot_roster")
            if pilot_worksheet:
                cell = pilot_worksheet.find(pilot_id)
                if cell:
                    pilot_worksheet.update_cell(cell.row, 8, project_id)  # current_assignment
                    pilot_worksheet.update_cell(cell.row, 7, "Assigned")  # status
            
            # Update drone sheet
            drone_worksheet = self._get_sheet("Drone Operations", "drone_fleet")
            if drone_worksheet:
                cell = drone_worksheet.find(drone_id)
                if cell:
                    drone_worksheet.update_cell(cell.row, 6, project_id)  # current_assignment
                    drone_worksheet.update_cell(cell.row, 4, "In Use")  # status
            
            # Clear all caches
            self._pilots_cache = None
            self._drones_cache = None
            self._missions_cache = None
            
            logger.info(f"Assigned {pilot_id} and {drone_id} to {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning to mission: {e}")
            return False
    
    def sync_all_data(self):
        """Sync all data between local cache and Google Sheets"""
        try:
            # Force refresh all caches
            self._pilots_cache = None
            self._drones_cache = None
            self._missions_cache = None
            
            # Get fresh data
            self.get_pilots()
            self.get_drones()
            self.get_missions()
            
            self._last_sync = datetime.now()
            logger.info("Data sync completed")
            
        except Exception as e:
            logger.error(f"Error syncing data: {e}")
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """Parse date string to date object"""
        if not date_str or date_str.strip() == '' or date_str == '–':
            return None
        
        try:
            # Try different date formats
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None
    
    def _load_local_pilots(self) -> List[Pilot]:
        """Load pilots from local CSV"""
        try:
            df = pd.read_csv('data/pilot_roster.csv')
            pilots = []
            
            for _, row in df.iterrows():
                skills = [s.strip() for s in str(row.get('skills', '')).split(',')]
                certs = [c.strip() for c in str(row.get('certifications', '')).split(',')]
                
                pilot = Pilot(
                    pilot_id=row.get('pilot_id', ''),
                    name=row.get('name', ''),
                    skills=skills,
                    certifications=certs,
                    location=row.get('location', ''),
                    status=row.get('status', 'Available'),
                    current_assignment=row.get('current_assignment', None),
                    available_from=self._parse_date(row.get('available_from', ''))
                )
                pilots.append(pilot)
            
            return pilots
            
        except Exception as e:
            logger.error(f"Error loading local pilots: {e}")
            return []
    
    def _load_local_drones(self) -> List[Drone]:
        """Load drones from local CSV"""
        try:
            df = pd.read_csv('data/drone_fleet.csv')
            drones = []
            
            for _, row in df.iterrows():
                capabilities = [c.strip() for c in str(row.get('capabilities', '')).split(',')]
                
                drone = Drone(
                    drone_id=row.get('drone_id', ''),
                    model=row.get('model', ''),
                    capabilities=capabilities,
                    status=row.get('status', 'Available'),
                    location=row.get('location', ''),
                    current_assignment=row.get('current_assignment', None),
                    maintenance_due=self._parse_date(row.get('maintenance_due', ''))
                )
                drones.append(drone)
            
            return drones
            
        except Exception as e:
            logger.error(f"Error loading local drones: {e}")
            return []
    
    def _load_local_missions(self) -> List[Mission]:
        """Load missions from local CSV"""
        try:
            df = pd.read_csv('data/missions.csv')
            missions = []
            
            for _, row in df.iterrows():
                skills = [s.strip() for s in str(row.get('required_skills', '')).split(',')]
                certs = [c.strip() for c in str(row.get('required_certs', '')).split(',')]
                
                mission = Mission(
                    project_id=row.get('project_id', ''),
                    client=row.get('client', ''),
                    location=row.get('location', ''),
                    required_skills=skills,
                    required_certs=certs,
                    start_date=self._parse_date(row.get('start_date', '')),
                    end_date=self._parse_date(row.get('end_date', '')),
                    priority=row.get('priority', 'Standard'),
                    assigned_pilot=None,
                    assigned_drone=None
                )
                missions.append(mission)
            
            return missions
            
        except Exception as e:
            logger.error(f"Error loading local missions: {e}")
            return []
    
    def _update_local_pilot_status(self, pilot_id: str, status: str):
        """Update pilot status in local CSV"""
        try:
            df = pd.read_csv('data/pilot_roster.csv')
            mask = df['pilot_id'] == pilot_id
            if mask.any():
                df.loc[mask, 'status'] = status
                df.to_csv('data/pilot_roster.csv', index=False)
        except Exception as e:
            logger.error(f"Error updating local pilot status: {e}")
    
    def _update_local_drone_status(self, drone_id: str, status: str):
        """Update drone status in local CSV"""
        try:
            df = pd.read_csv('data/drone_fleet.csv')
            mask = df['drone_id'] == drone_id
            if mask.any():
                df.loc[mask, 'status'] = status
                df.to_csv('data/drone_fleet.csv', index=False)
        except Exception as e:
            logger.error(f"Error updating local drone status: {e}")