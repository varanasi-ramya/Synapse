# runs in each backend container (b1,b2,b3)
import socket
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    # JSON response containing socket.gethostname()
    return {
        "status": "success",
        "message": "Response served by container",
        "hostname": socket.gethostname()
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}