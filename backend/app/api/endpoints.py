from fastapi import APIRouter
from app.api.routers.industries import router as industries_router
from app.api.routers.occupations import router as occupations_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.job_detail import router as job_detail_router  # Add this
from app.api.routers.skills import router as skills_router  # Add this
from app.api.routers.forecast import router as forecast_router  # Add this
from app.api.routers.home import router as home_router
from app.api.routers.salary_employment import router as salary_employment_router
from app.api.routers.search import router as search_router


print("✅ Imported industries router")
print("✅ Imported occupations router")  
print(f"✅ Imported jobs router: {jobs_router}")  # Debug line

router = APIRouter()

router.include_router(industries_router)
router.include_router(occupations_router)
router.include_router(jobs_router)  # Make sure this line is present!
router.include_router(job_detail_router)  # Add this
router.include_router(skills_router)  # Add this
router.include_router(forecast_router)  # Add this
router.include_router(home_router)
router.include_router(salary_employment_router)
router.include_router(search_router)


print(f"✅ Total routes after including: {len(router.routes)}")  # Debug line

@router.get("/health")
async def health_check():
    return {"status": "ok", "routers": ["industries", "occupations", "jobs", "job-detail", "skills", "forecast", "search"]}