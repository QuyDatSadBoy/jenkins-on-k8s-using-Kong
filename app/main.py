from typing import Union
from fastapi import FastAPI
import os

app = FastAPI(root_path="/api")

@app.get("/")
def read_root():
    return {
        "message": "Hello from FastAPI on K8s on QuyDat09 13 09 112!",
        "version": "v1.0",
        "pod": os.environ.get("HOSTNAME", "unknown")
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}