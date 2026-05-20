from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import asyncio
from pydantic import BaseModel
from google.genai import types

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService

from agent import get_github_card_agent
from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card

# Create the agent and attach tools at construction time
github_card_agent = get_github_card_agent(
    tools=[scrape_github, analyze_profile, generate_card_html, save_card]
)

app = FastAPI(title="GitHub Dev Card Generator")

# Services
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

# Runner
runner = Runner(
    app_name="github_card_generator",
    agent=github_card_agent,
    session_service=session_service,
    memory_service=memory_service
)

# Static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(os.path.join(static_dir, "cards"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    # Fallback to parent frontend directory for local dev convenience
    fallback_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    if os.path.exists(fallback_path):
        return FileResponse(fallback_path)
    raise HTTPException(status_code=404, detail="index.html not found")

class GenerateRequest(BaseModel):
    username: str

@app.post("/generate")
async def generate(request: GenerateRequest):
    username = request.username
    session_id = f"session_{username}"
    user_id = "user_123"
    
    # Run the agent via the runner
    try:
        # Ensure session exists
        session = await session_service.get_session(
            app_name="github_card_generator",
            user_id=user_id,
            session_id=session_id
        )
        if not session:
            await session_service.create_session(
                app_name="github_card_generator",
                user_id=user_id,
                session_id=session_id
            )

        # We use run_async which returns an AsyncGenerator
        async for _ in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Generate a dev card for {username}")]
            )
        ):
            pass
        
        # The agent's final step is save_card which returns the URL
        card_path = f"static/cards/{username}.html"
        full_path = os.path.join(os.path.dirname(__file__), card_path)
        
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return {
                "status": "success",
                "url": f"/static/cards/{username}.html",
                "html": html_content
            }
        else:
            return {"status": "error", "message": "Card was not generated correctly"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/card/{username}")
async def get_card(username: str):
    card_path = os.path.join(static_dir, "cards", f"{username}.html")
    if os.path.exists(card_path):
        return FileResponse(card_path)
    raise HTTPException(status_code=404, detail="Card not found")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
