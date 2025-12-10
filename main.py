import os
import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from multiprocessing import Process, Queue
from browser_use import Agent, Browser

load_dotenv()

# ------------------------------------------------------
# GLOBAL STATE
# ------------------------------------------------------
class AgentState:
    running = False

state = AgentState()

# Use multiprocessing Queue
log_queue = Queue()


# ------------------------------------------------------
# FASTAPI
# ------------------------------------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ------------------------------------------------------
# REQUEST MODEL
# ------------------------------------------------------
class PromptRequest(BaseModel):
    prompt: str


# ------------------------------------------------------
# LOGGING HANDLER (CHILD PROCESS)
# ------------------------------------------------------
class ChildProcessQueueHandler(logging.Handler):
    """Send logs from child process to main process queue."""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        msg = self.format(record)
        self.queue.put(msg)


# ------------------------------------------------------
# CHILD PROCESS RUNNER
# ------------------------------------------------------
def run_agent_process(prompt: str, queue: Queue):
    """
    This runs INSIDE the new process.
    We must re-create logging handlers here!
    """
    # New event loop
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()

    # ------------------------------
    # Attach logging handler INSIDE child process
    # ------------------------------
    handler = ChildProcessQueueHandler(queue)
    handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

    browser_logger = logging.getLogger("browser_use")
    browser_logger.handlers.clear()
    browser_logger.setLevel(logging.INFO)
    browser_logger.addHandler(handler)

    # Also send root logs
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    async def _run_task():
        queue.put("⚙️ Starting agent task...")

        state.running = True

        browser = Browser(keep_alive=False, headless=False)
        await browser.start()

        agent = Agent(task=prompt, model="gemini-2.5-pro", browser=browser)

        await agent.run()

        # Cleanup safely
        try:
            await browser.kill()
        except:
            pass

        try:
            await browser.playwright.close()
        except:
            pass

        try:
            browser.session_manager.reset(force=True)
        except:
            pass

        queue.put("✅ Automation done. Browser closed successfully.")
        state.running = False

    loop.run_until_complete(_run_task())


# ------------------------------------------------------
# START TASK
# ------------------------------------------------------
@app.post("/run-agent")
async def run_agent(req: PromptRequest):

    if state.running:
        return {"status": "error", "message": "⚠️ Agent already running"}

    # Clear old logs
    while not log_queue.empty():
        log_queue.get_nowait()

    # Start new isolated process
    process = Process(target=run_agent_process, args=(req.prompt, log_queue))
    process.start()

    return {"status": "started"}


# ------------------------------------------------------
# LIVE LOG STREAM
# ------------------------------------------------------
@app.websocket("/logs")
async def websocket_logs(ws: WebSocket):
    await ws.accept()
    await ws.send_text("🔌 Connected to log stream...")

    try:
        while True:
            try:
                msg = log_queue.get_nowait()
                await ws.send_text(msg)
            except:
                pass

            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass


@app.get("/health")
def health():
    return {"status": "ok"}
