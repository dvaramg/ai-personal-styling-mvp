from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.recommend import router as recommend_router
from app.api.routes.wardrobe import router as wardrobe_router
from app.api.routes.history import router as history_router
from app.api.routes.body_analysis import router as body_analysis_router
from app.api.hat_recommend import router as hat_recommend_router

from dotenv import load_dotenv
load_dotenv( )

app = FastAPI(title="AI Personal Styling System", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["health"])
app.include_router(recommend_router, prefix="/api/v1", tags=["recommend"])
app.include_router(wardrobe_router, prefix="/api/v1", tags=["wardrobe"])
app.include_router(history_router, prefix="/api/v1", tags=["history"])
app.include_router(body_analysis_router, prefix="/api/v1", tags=["body-analysis"])
app.include_router(hat_recommend_router, prefix="/api/v1", tags=["hat-recommend"])