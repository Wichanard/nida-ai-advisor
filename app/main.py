import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import subprocess

from app.services.agent_engine import NIDAAgentEngine
from app.models.database import init_db, get_chat_history
from app.routers import admin, line

# Initialize database on startup
init_db()

# Rate Limiter Configuration
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="NIDA AI Enterprise API",
    description="Next-generation API backend powering the NIDA conversational AI.",
    version="3.0.0",
)

# Add Rate Limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error. Please try again later."},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(line.router)

class ChatRequest(BaseModel):
    session_id: str
    message: str
    degree_filter: str = "ทั้งหมด"
    faculty_filter: str = "ทั้งหมด"
    study_mode_filter: str = "ทั้งหมด"

scheduler = AsyncIOScheduler()

def run_social_listening_collectors():
    print("Running Social Listening Collectors...")
    try:
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "social_listening", "run_collector.py")
        subprocess.run(["python", script_path], check=True)
        print("Social Listening Collectors completed successfully.")
    except Exception as e:
        print(f"Error running collectors: {e}")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "NIDA AI Enterprise Engine is running."}

@app.on_event("startup")
async def startup_event():
    from app.tasks.alert_agent import start_alert_agent_bg_task
    start_alert_agent_bg_task()
    
    # Start the scheduler
    scheduler.add_job(run_social_listening_collectors, 'interval', hours=12) # Run every 12 hours
    scheduler.start()

@app.post("/webhook/facebook")
@limiter.limit("100/minute")
async def facebook_webhook(request: Request):
    """Endpoint for Facebook Messenger Webhook."""
    return {"status": "success"}

@app.get("/webhook/facebook")
async def facebook_webhook_verify(request: Request):
    """Facebook requires GET endpoint for webhook verification."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    return int(challenge) if challenge else "Verification failed"

@app.get("/api/history")
@limiter.limit("50/minute")
async def get_history_endpoint(request: Request, session_id: str):
    """Fetch chat history for a session."""
    if not session_id:
        return {"history": []}
    
    try:
        raw_history = get_chat_history(session_id=session_id, limit=50)
        formatted = []
        for msg in raw_history:
            formatted.append({
                "id": str(msg["id"]),
                "role": "user" if msg["sender"] == "user" else "assistant",
                "content": msg["message"]
            })
        return {"history": formatted}
    except Exception as e:
        print(f"Error fetching history: {e}")
        return {"history": []}

@app.get("/api/sessions")
@limiter.limit("50/minute")
async def get_sessions_endpoint(request: Request, user_id: str = "guest", search: str = None):
    """Fetch all chat sessions for a user."""
    from app.models.database import get_all_chat_sessions
    try:
        sessions = get_all_chat_sessions(user_id=user_id, search_query=search)
        return {"sessions": sessions}
    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return {"sessions": []}


@app.get("/api/courses")
@limiter.limit("20/minute")
async def get_courses_endpoint(request: Request):
    """Fetch all courses for the comparison page."""
    import json
    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        courses_path = os.path.join(base_dir, "data", "courses.json")
        with open(courses_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading courses.json: {e}")
        return []

@app.post("/api/chat")
@limiter.limit("20/minute")
async def chat_endpoint(request: Request, req: ChatRequest):
    """Streaming endpoint for Next.js frontend to consume."""
    def generate():
        try:
            for chunk in NIDAAgentEngine.execute_chat_stream(
                session_id=req.session_id,
                user_message=req.message,
                degree_filter=req.degree_filter,
                faculty_filter=req.faculty_filter,
                study_mode_filter=req.study_mode_filter
            ):
                yield chunk
        except Exception as e:
            print(f"Chat stream error: {e}")
            yield f"ขออภัยครับ เกิดข้อผิดพลาดในระบบประมวลผล ({str(e)})"

    return StreamingResponse(generate(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
