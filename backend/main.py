"""
Vigil Backend API — Main Application Entry Point.
Phase 0 Basic Scaffold.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Vigil API",
    description="Autonomous Fraud Investigation Agent Backend",
    version="0.1.0"
)

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """System health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "message": "Vigil backend scaffold initialized."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
