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