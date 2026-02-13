from fastapi import APIRouter
from app.api.routers.industries import router as industries_router
from app.api.routers.occupations import router as occupations_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.job_detail import router as job_detail_router  # Add this

print("✅ Imported industries router")
print("✅ Imported occupations router")  
print(f"✅ Imported jobs router: {jobs_router}")  # Debug line

router = APIRouter()

router.include_router(industries_router)
router.include_router(occupations_router)
router.include_router(jobs_router)  # Make sure this line is present!
router.include_router(job_detail_router)  # Add this

print(f"✅ Total routes after including: {len(router.routes)}")  # Debug line

@router.get("/health")
async def health_check():
    return {"status": "ok", "routers": ["industries", "occupations", "jobs"]}