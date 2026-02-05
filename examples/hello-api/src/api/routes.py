"""API routes - thin wrapper around core logic."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.core.greeter import greet

app = FastAPI(title="Hello API", version="1.0.0")


class GreetRequest(BaseModel):
    name: str
    formal: bool = False


@app.get("/")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/greet/{name}")
def greet_simple(name: str):
    """Simple greeting endpoint."""
    try:
        return {"greeting": greet(name)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/greet")
def greet_custom(request: GreetRequest):
    """Custom greeting with options."""
    try:
        return {"greeting": greet(request.name, request.formal)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
