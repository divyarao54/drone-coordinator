from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, date
import logging

from api.agents.coordinator_agent import CoordinatorAgent
from api.services.sheets_service import SheetsService
from api.services.matching_service import MatchingService
from api.models.pilot import Pilot, PilotUpdate
from api.models.drone import Drone, DroneUpdate
from api.models.mission import Mission, MissionCreate
from api.agents.conflict_detector import ConflictDetector

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Drone Operations Coordinator API",
    description="AI agent for managing drone operations",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
sheets_service = SheetsService()
matching_service = MatchingService()
coordinator_agent = CoordinatorAgent(sheets_service, matching_service)
conflict_detector = ConflictDetector(sheets_service)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Drone Operations Coordinator API")
    try:
        sheets_service.authenticate()
        logger.info("Google Sheets authentication successful")
    except Exception as e:
        logger.error(f"Google Sheets authentication failed: {e}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Drone Operations Coordinator API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        sheets_service = SheetsService()
        sheets_service.authenticate()
        
        pilots = sheets_service.get_pilots()
        drones = sheets_service.get_drones()
        missions = sheets_service.get_missions()
        
        # Count available pilots
        available_pilots = 0
        for p in pilots:
            if p.status and p.status.lower() == "available":
                available_pilots += 1
        
        # Count available drones
        available_drones = 0
        for d in drones:
            if d.status and d.status.lower() == "available":
                available_drones += 1
        
        # Count active missions (end date is today or in future)
        today = datetime.now().date()
        active_missions = 0
        for m in missions:
            try:
                # m.end_date could be a date object OR a string
                end_date = None
                
                if isinstance(m.end_date, date):
                    # Already a date object
                    end_date = m.end_date
                elif isinstance(m.end_date, str):
                    # Try to parse string date
                    try:
                        end_date = datetime.strptime(m.end_date, '%Y-%m-%d').date()
                    except ValueError:
                        # Try other formats
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                            try:
                                end_date = datetime.strptime(m.end_date, fmt).date()
                                break
                            except ValueError:
                                continue
                elif m.end_date is None:
                    # No end date, skip
                    continue
                
                if end_date and end_date >= today:
                    active_missions += 1
            except Exception as e:
                logger.warning(f"Error processing mission date for {m.project_id}: {e}")
                continue
        
        # Count pending assignments (missions without assigned pilot)
        pending_assignments = 0
        for m in missions:
            if not m.assigned_pilot or str(m.assigned_pilot).strip() in ['', '–', 'None', 'nan']:
                pending_assignments += 1
        
        return {
            "available_pilots": available_pilots,
            "available_drones": available_drones,
            "active_missions": active_missions,
            "pending_assignments": pending_assignments,
            "last_sync": datetime.now().isoformat(),
            "available_pilots_change": 0,
            "available_drones_change": 0,
            "total_pilots": len(pilots),
            "total_drones": len(drones),
            "total_missions": len(missions),
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        import traceback
        logger.error(traceback.format_exc())

@app.get("/pilots")
async def get_pilots(status: str = None, location: str = None):
    """Get all pilots with optional filters"""
    try:
        pilots = sheets_service.get_pilots()
        
        # Apply filters
        if status:
            pilots = [p for p in pilots if p.status == status]
        if location:
            pilots = [p for p in pilots if p.location == location]
        
        return [p.dict() for p in pilots]
    except Exception as e:
        logger.error(f"Error getting pilots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pilots/{pilot_id}")
async def get_pilot(pilot_id: str):
    """Get specific pilot"""
    try:
        pilot = sheets_service.get_pilot(pilot_id)
        if not pilot:
            raise HTTPException(status_code=404, detail="Pilot not found")
        return pilot.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pilot {pilot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/pilots/{pilot_id}/status")
async def update_pilot_status(pilot_id: str, update: PilotUpdate):
    """Update pilot status"""
    try:
        success = sheets_service.update_pilot_status(pilot_id, update.status)
        if not success:
            raise HTTPException(status_code=404, detail="Pilot not found")
        
        # Check for conflicts after update
        conflicts = conflict_detector.check_pilot_conflicts(pilot_id)
        
        return {
            "message": f"Pilot {pilot_id} status updated to {update.status}",
            "conflicts": conflicts
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating pilot {pilot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/drones")
async def get_drones(status: str = None, location: str = None):
    """Get all drones with optional filters"""
    try:
        drones = sheets_service.get_drones()
        
        # Apply filters
        if status:
            drones = [d for d in drones if d.status == status]
        if location:
            drones = [d for d in drones if d.location == location]
        
        return [d.dict() for d in drones]
    except Exception as e:
        logger.error(f"Error getting drones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/missions")
async def get_missions(priority: str = None, location: str = None):
    """Get all missions with optional filters"""
    try:
        missions = sheets_service.get_missions()
        
        # Apply filters
        if priority:
            missions = [m for m in missions if m.priority == priority]
        if location:
            missions = [m for m in missions if m.location == location]
        
        return [m.dict() for m in missions]
    except Exception as e:
        logger.error(f"Error getting missions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/missions/{project_id}/available-pilots")
async def get_available_pilots_for_mission(project_id: str):
    """Get available pilots for a specific mission"""
    try:
        mission = sheets_service.get_mission(project_id)
        if not mission:
            raise HTTPException(status_code=404, detail="Mission not found")
        
        available_pilots = matching_service.find_matching_pilots(mission)
        return [p.dict() for p in available_pilots]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available pilots for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/missions/{project_id}/available-drones")
async def get_available_drones_for_mission(project_id: str):
    """Get available drones for a specific mission"""
    try:
        mission = sheets_service.get_mission(project_id)
        if not mission:
            raise HTTPException(status_code=404, detail="Mission not found")
        
        available_drones = matching_service.find_matching_drones(mission)
        return [d.dict() for d in available_drones]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available drones for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/assign")
async def assign_resources(project_id: str, pilot_id: str, drone_id: str):
    """Assign pilot and drone to mission"""
    try:
        result = coordinator_agent.assign_mission(project_id, pilot_id, drone_id)
        
        if result["success"]:
            return {
                "message": f"Successfully assigned {pilot_id} and {drone_id} to {project_id}",
                "assignment": result["assignment"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        logger.error(f"Error assigning resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conflicts")
async def get_conflicts():
    """Get all detected conflicts"""
    try:
        conflicts = conflict_detector.detect_all_conflicts()
        return conflicts
    except Exception as e:
        logger.error(f"Error getting conflicts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_with_agent(message: dict):
    """Chat with the coordinator agent"""
    try:
        user_message = message.get("message", "")
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        response = coordinator_agent.process_query(user_message)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync")
async def sync_with_sheets(background_tasks: BackgroundTasks):
    """Sync data with Google Sheets"""
    try:
        # Run sync in background
        background_tasks.add_task(sheets_service.sync_all_data)
        return {"message": "Sync started in background"}
    except Exception as e:
        logger.error(f"Error syncing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recent-activity")
async def get_recent_activity():
    """Get recent system activity"""
    # This would typically come from a database
    return [
        {
            "timestamp": datetime.now().isoformat(),
            "message": "System started",
            "type": "system"
        }
    ]

# Assignment Tracking Endpoints
@app.get("/assignments")
async def get_all_assignments():
    """Get all current assignments"""
    try:
        sheets_service = SheetsService()
        sheets_service.authenticate()
        
        missions = sheets_service.get_missions()
        pilots = sheets_service.get_pilots()
        drones = sheets_service.get_drones()
        
        assignments = []
        for mission in missions:
            if mission.assigned_pilot and mission.assigned_drone:
                pilot = next((p for p in pilots if p.pilot_id == mission.assigned_pilot), None)
                drone = next((d for d in drones if d.drone_id == mission.assigned_drone), None)
                
                assignment = {
                    "project_id": mission.project_id,
                    "client": mission.client,
                    "location": mission.location,
                    "start_date": mission.start_date,
                    "end_date": mission.end_date,
                    "priority": mission.priority,
                    "assigned_pilot": {
                        "pilot_id": pilot.pilot_id if pilot else mission.assigned_pilot,
                        "name": pilot.name if pilot else "Unknown",
                        "skills": pilot.skills if pilot else [],
                        "location": pilot.location if pilot else "Unknown"
                    } if pilot else {"pilot_id": mission.assigned_pilot},
                    "assigned_drone": {
                        "drone_id": drone.drone_id if drone else mission.assigned_drone,
                        "model": drone.model if drone else "Unknown",
                        "capabilities": drone.capabilities if drone else [],
                        "location": drone.location if drone else "Unknown"
                    } if drone else {"drone_id": mission.assigned_drone},
                    "status": "Active" if isinstance(mission.end_date, date) and mission.end_date >= datetime.now().date() else "Completed"
                }
                assignments.append(assignment)
        
        return assignments
    except Exception as e:
        logger.error(f"Error getting assignments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/assignments/{project_id}/reassign")
async def reassign_mission(project_id: str, reassignment: dict):
    """Reassign resources to a mission"""
    try:
        sheets_service = SheetsService()
        
        # Get current assignment
        mission = sheets_service.get_mission(project_id)
        if not mission:
            raise HTTPException(status_code=404, detail="Mission not found")
        
        old_pilot_id = mission.assigned_pilot
        old_drone_id = mission.assigned_drone
        
        # New assignments
        new_pilot_id = reassignment.get("pilot_id")
        new_drone_id = reassignment.get("drone_id")
        
        if not new_pilot_id or not new_drone_id:
            raise HTTPException(status_code=400, detail="Both pilot_id and drone_id are required")
        
        # Check if new resources are available
        matching_service = MatchingService()
        pilots = sheets_service.get_pilots()
        drones = sheets_service.get_drones()
        
        new_pilot = next((p for p in pilots if p.pilot_id == new_pilot_id), None)
        new_drone = next((d for d in drones if d.drone_id == new_drone_id), None)
        
        if not new_pilot:
            raise HTTPException(status_code=404, detail=f"Pilot {new_pilot_id} not found")
        if not new_drone:
            raise HTTPException(status_code=404, detail=f"Drone {new_drone_id} not found")
        
        # Check conflicts
        conflict_detector = ConflictDetector(sheets_service)
        conflicts = conflict_detector.check_assignment_conflicts(mission, new_pilot, new_drone)
        
        if conflicts:
            conflict_messages = "\n".join([c["message"] for c in conflicts])
            raise HTTPException(status_code=400, detail=f"Reassignment conflicts:\n{conflict_messages}")
        
        # Perform reassignment
        success = sheets_service.assign_to_mission(project_id, new_pilot_id, new_drone_id)
        
        if success:
            # Free up old resources if they're still assigned to this mission
            if old_pilot_id:
                sheets_service.update_pilot_status(old_pilot_id, "Available")
            if old_drone_id:
                sheets_service.update_drone_status(old_drone_id, "Available")
            
            return {
                "message": f"Successfully reassigned {project_id}",
                "old_assignment": {"pilot_id": old_pilot_id, "drone_id": old_drone_id},
                "new_assignment": {"pilot_id": new_pilot_id, "drone_id": new_drone_id}
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update assignment in sheets")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reassigning mission: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Drone Inventory Endpoints
@app.get("/drones/search")
async def search_drones(
    capability: str = None,
    location: str = None,
    status: str = None,
    available_only: bool = False
):
    """Search drones with filters"""
    try:
        sheets_service = SheetsService()
        sheets_service.authenticate()
        
        drones = sheets_service.get_drones()
        
        # Apply filters
        filtered_drones = drones
        
        if capability:
            filtered_drones = [d for d in filtered_drones if capability.lower() in [c.lower() for c in d.capabilities]]
        
        if location:
            filtered_drones = [d for d in filtered_drones if d.location.lower() == location.lower()]
        
        if status:
            filtered_drones = [d for d in filtered_drones if d.status.lower() == status.lower()]
        
        if available_only:
            filtered_drones = [d for d in filtered_drones if d.status == "Available"]
        
        # Sort by maintenance due date
        filtered_drones.sort(key=lambda x: x.maintenance_due if x.maintenance_due else date(9999, 12, 31))
        
        return [d.dict() for d in filtered_drones]
        
    except Exception as e:
        logger.error(f"Error searching drones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/drones/maintenance")
async def get_maintenance_drones(days_threshold: int = 7):
    """Get drones needing maintenance"""
    try:
        sheets_service = SheetsService()
        sheets_service.authenticate()
        
        drones = sheets_service.get_drones()
        today = datetime.now().date()
        
        maintenance_drones = []
        for drone in drones:
            if drone.maintenance_due:
                days_until = (drone.maintenance_due - today).days
                if days_until <= days_threshold:
                    maintenance_drones.append({
                        **drone.dict(),
                        "days_until_maintenance": days_until,
                        "status": "OVERDUE" if days_until < 0 else f"Due in {days_until} days"
                    })
        
        # Sort by urgency
        maintenance_drones.sort(key=lambda x: x["days_until_maintenance"])
        
        return maintenance_drones
        
    except Exception as e:
        logger.error(f"Error getting maintenance drones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/drones/{drone_id}/status")
async def update_drone_status(drone_id: str, update: DroneUpdate):
    """Update drone status"""
    try:
        sheets_service = SheetsService()
        
        success = sheets_service.update_drone_status(drone_id, update.status)
        if not success:
            raise HTTPException(status_code=404, detail="Drone not found")
        
        # If updating assignment
        if update.current_assignment:
            # Update drone assignment logic here
            pass
        
        return {
            "message": f"Drone {drone_id} status updated to {update.status}",
            "drone_id": drone_id,
            "new_status": update.status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating drone status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/drones/{drone_id}/maintenance")
async def update_drone_maintenance(drone_id: str, maintenance_date: dict):
    """Update drone maintenance date"""
    try:
        sheets_service = SheetsService()
        
        new_date_str = maintenance_date.get("maintenance_due")
        if not new_date_str:
            raise HTTPException(status_code=400, detail="maintenance_due date required")
        
        # Parse date
        try:
            new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Update in Google Sheets
        worksheet = sheets_service._get_worksheet("drone_fleet")
        if not worksheet:
            raise HTTPException(status_code=500, detail="Cannot access drone fleet worksheet")
        
        cell = worksheet.find(drone_id)
        if not cell:
            raise HTTPException(status_code=404, detail="Drone not found")
        
        # Update maintenance due date (assuming column G)
        worksheet.update_cell(cell.row, 7, new_date_str)
        
        # Clear cache
        sheets_service._drones_cache = None
        
        return {
            "message": f"Drone {drone_id} maintenance updated to {new_date_str}",
            "drone_id": drone_id,
            "maintenance_due": new_date_str
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating drone maintenance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/drones/deployment")
async def get_deployment_status():
    """Get deployment status of all drones"""
    try:
        sheets_service = SheetsService()
        sheets_service.authenticate()
        
        drones = sheets_service.get_drones()
        missions = sheets_service.get_missions()
        
        deployment_status = []
        for drone in drones:
            # Find mission assigned to this drone
            assigned_mission = next(
                (m for m in missions if m.assigned_drone == drone.drone_id),
                None
            )
            
            status = {
                "drone_id": drone.drone_id,
                "model": drone.model,
                "status": drone.status,
                "location": drone.location,
                "assigned_to": assigned_mission.project_id if assigned_mission else None,
                "client": assigned_mission.client if assigned_mission else None,
                "mission_dates": f"{assigned_mission.start_date} to {assigned_mission.end_date}" if assigned_mission else None,
                "maintenance_due": drone.maintenance_due,
                "capabilities": drone.capabilities
            }
            
            # Calculate maintenance urgency
            if drone.maintenance_due:
                today = datetime.now().date()
                days_until = (drone.maintenance_due - today).days
                status["maintenance_urgency"] = "OVERDUE" if days_until < 0 else f"{days_until} days"
            
            deployment_status.append(status)
        
        return deployment_status
        
    except Exception as e:
        logger.error(f"Error getting deployment status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)