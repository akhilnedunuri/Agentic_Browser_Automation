import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from browser_use import Agent, Browser
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

# ---------------- Thread state ----------------
class AgentThreadState:
    loop = None
    browser = None

state = AgentThreadState()
executor = ThreadPoolExecutor(max_workers=1)

app = FastAPI(
    title="Stable Browser Automation API",
    description="Crash-proof Browser + Playwright + Gemini Agent",
    version="9.1.0"
)

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Frontend ----------------
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# ---------------- Browser Initialization ----------------
async def start_browser():
    """
    Headless=False to see automation, uses Xvfb in Docker for virtual display.
    """
    browser = Browser(
        keep_alive=True,
        headless=False  # visual mode
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

# ---------------- Extract last step ----------------
def extract_last_step(agent_result):
    """
    Extract ONLY:
    - last step done text (final step)
    - final result
    - success message
    """
    try:
        history = agent_result.history
        last_step = history[-1]  # last step only
        if hasattr(last_step, "done") and last_step.done:
            done_text = last_step.done
        elif hasattr(last_step, "extracted_content"):
            done_text = last_step.extracted_content
        else:
            done_text = str(agent_result)
    except Exception as e:
        print("LAST STEP PARSE ERROR:", e)
        done_text = str(agent_result)

    output = (
        f"📄 Final Result:\n{done_text}\n\n"
        "INFO     [Agent] ✅ Task completed successfully"
    )
    return output

# ---------------- Run Agent ----------------
def run_agent_sync(prompt: str):
    loop, browser = init_thread_if_needed()

    async def _run():
        agent = Agent(
            task=prompt,
            model="gemini-2.5-pro",
            browser=browser,
            headless=False  # visual automation
        )
        result = await agent.run()
        clean_output = extract_last_step(result)
        return clean_output

    return loop.run_until_complete(_run())

# ---------------- Public API — Run Agent ----------------
@app.post("/run-agent")
async def run_agent(prompt: str):
    if not os.environ.get("GOOGLE_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_API_KEY missing",
        )

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            executor,
            lambda: run_agent_sync(prompt)
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

# ---------------- Public API — Close Browser ----------------
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
