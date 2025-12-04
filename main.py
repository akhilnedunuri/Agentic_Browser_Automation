import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from browser_use import Agent, Browser
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

# ---------------- Thread / Browser State ----------------
class AgentThreadState:
    loop = None
    browser = None

state = AgentThreadState()
executor = ThreadPoolExecutor(max_workers=1)

app = FastAPI(
    title="Stable Browser Automation API",
    description="Crash-proof Browser + Playwright + Gemini Agent",
    version="10.0.0"
)

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Frontend Serving ----------------
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_frontend():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_file):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_file)

# ---------------- Pydantic Request Model ----------------
class PromptRequest(BaseModel):
    prompt: str

# ---------------- Browser Initialization ----------------
async def start_browser():
    browser = Browser(
        keep_alive=True,
        headless=False
    )
    await browser.start()
    return browser

def init_thread_if_needed():
    if state.loop is None:
        state.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(state.loop)
    if state.browser is None:
        state.browser = state.loop.run_until_complete(start_browser())
    return state.loop, state.browser

# ---------------- Extract Final Agent Step ----------------
def extract_last_step(agent_result):
    try:
        last = agent_result.history[-1]
        if getattr(last, "done", None):
            done_text = last.done
        elif getattr(last, "extracted_content", None):
            done_text = last.extracted_content
        else:
            done_text = str(agent_result)
    except:
        done_text = str(agent_result)

    return (
        f"📄 Final Result:\n{done_text}\n\n"
        "INFO     [Agent] ✅ Task completed successfully"
    )

# ---------------- Run Agent (Sync Wrapper) ----------------
def run_agent_sync(prompt: str):
    loop, browser = init_thread_if_needed()

    async def _run():
        agent = Agent(
            task=prompt,
            model="gemini-2.5-pro",
            browser=browser,
            headless=False
        )
        result = await agent.run()
        return extract_last_step(result)

    return loop.run_until_complete(_run())

# ---------------- API: Run Agent ----------------
@app.post("/run-agent")
async def run_agent(req: PromptRequest):
    if not os.environ.get("GOOGLE_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_API_KEY missing"
        )

    prompt = req.prompt

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            executor, lambda: run_agent_sync(prompt)
        )
        return {"status": "success", "output": result}

    except Exception as e:
        print("ERROR:", e)

        def reset_browser():
            if state.browser:
                state.loop.run_until_complete(state.browser.kill())
            state.browser = None

        executor.submit(reset_browser)

        raise HTTPException(
            status_code=500,
            detail=f"Agent Execution Error: {e}"
        )

# ---------------- API: Close Browser ----------------
@app.post("/close-browser")
async def close_browser():
    if state.browser is None:
        return {"message": "No active browser session"}

    def kill_browser():
        state.loop.run_until_complete(state.browser.kill())
        state.browser = None

    executor.submit(kill_browser)
    return {"message": "Browser closed"}

# ---------------- Health Check ----------------
@app.get("/health")
def health():
    return {"message": "Browser automation running"}
