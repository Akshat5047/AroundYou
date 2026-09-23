from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.climate import router as climate_router
from routes.budget import router as budget_router
from routes.crowd import router as crowd_router
from routes.transport import router as transport_router
from routes.review import router as review_router
from routes.rag import router as rag_router
from routes.agent import router as agent_router
from routes.cleanliness import router as cleanliness_router


app = FastAPI(
    title="Around You API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(climate_router)
app.include_router(budget_router)
app.include_router(crowd_router)
app.include_router(transport_router)
app.include_router(review_router)
app.include_router(rag_router)
app.include_router(agent_router)
app.include_router(cleanliness_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "Around You API",
    }