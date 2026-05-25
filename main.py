# main.py
import uvicorn
from fastapi import FastAPI

from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="FamilyFinance API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Module routers are mounted here as each epic completes them.
# e.g.: app.include_router(auth_router, prefix="/v1/auth")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
