import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from browser_use import Agent, Browser

load_dotenv()

# ---------------- Thread + Browser State ----------------
class AgentThreadState:
    loop = None
    browser = None

state = AgentThreadState()
executor = ThreadPoolExecutor(max_workers=1)

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Frontend Serving ----------------
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_frontend():
    index = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index):
        raise HTTPException(404, "index.html missing")
    return FileResponse(index)


# ---------------- Pydantic ----------------
class PromptRequest(BaseModel):
    prompt: str


# ---------------- Browser Init ----------------
async def start_browser():
    browser = Browser(keep_alive=True, headless=False)
    await browser.start()
    return browser


def init_thread():
    """Initialize background event loop and browser only once."""
    if state.loop is None:
        state.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(state.loop)

    if state.browser is None:
        state.browser = state.loop.run_until_complete(start_browser())

    return state.loop, state.browser


# ---------------- Agent Wrapper ----------------
def extract_last(agent_result):
    try:
        last = agent_result.history[-1]
        if hasattr(last, "done") and last.done:
            return last.done
        if hasattr(last, "extracted_content") and last.extracted_content:
            return last.extracted_content
    except:
        pass
    return str(agent_result)


def run_agent_sync(prompt):
    loop, browser = init_thread()

    async def _run():
        agent = Agent(task=prompt, model="gemini-2.5-pro", browser=browser)
        result = await agent.run()
        return extract_last(result)

    return loop.run_until_complete(_run())


# ---------------- API: RUN AGENT ----------------
@app.post("/run-agent")
async def run_agent(req: PromptRequest):
    if not os.environ.get("GOOGLE_API_KEY"):
        return {"status": "error", "output": "Missing GOOGLE_API_KEY"}

    try:
        output = await asyncio.get_event_loop().run_in_executor(
            executor, lambda: run_agent_sync(req.prompt)
        )
        return {"status": "success", "output": output}

    except Exception as e:
        print("AGENT ERROR:", e)

        # Attempt browser cleanup
        try:
            if state.browser:
                state.loop.run_until_complete(state.browser.kill())
            state.browser = None
        except:
            pass

        return {
            "status": "error",
            "output": f"Agent crashed: {str(e)}"
        }  # <---- ALWAYS RETURN VALID JSON


# ---------------- API: CLOSE BROWSER ----------------
@app.post("/close-browser")
async def close_browser():
    try:
        if state.browser:
            state.loop.run_until_complete(state.browser.kill())
        state.browser = None
        return {"status": "success", "message": "Browser closed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/health")
def health():
    return {"status": "ok"}
