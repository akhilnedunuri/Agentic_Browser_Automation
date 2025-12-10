const runBtn = document.getElementById("runBtn");
const output = document.getElementById("output");

let ws = null;

function append(text) {
    output.textContent += text + "\n";
    output.scrollTop = output.scrollHeight;
}

function clearOutput() {
    output.textContent = "";
}

runBtn.addEventListener("click", async () => {

    const prompt = document.getElementById("prompt").value.trim();
    if (!prompt) return alert("Enter a prompt!");

    clearOutput();
    append("⚙️ Starting agent...\nWaiting for logs...\n");

    // --- CLOSE OLD WS ---
    if (ws && (ws.readyState === 0 || ws.readyState === 1)) {
        try { ws.close(); } catch {}
    }

    // --- START AGENT ---
    const res = await fetch("/run-agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
    });

    const data = await res.json();
    if (data.status !== "started") {
        append("❌ Failed to start agent: " + data.message);
        return;
    }

    // --- OPEN NEW WS DELAYED ---
    // waiting 150ms ensures backend event loop + logs are ready
    setTimeout(() => {

        ws = new WebSocket("ws://127.0.0.1:8000/logs");

        ws.onopen = () => {
            append("🔌 Connected to log stream...\n");
        };

        ws.onmessage = (event) => {
            append(event.data);
        };

        ws.onerror = () => append("❌ WebSocket error");

        ws.onclose = () => append("\n🔌 Log stream closed.");

    }, 150);
});
