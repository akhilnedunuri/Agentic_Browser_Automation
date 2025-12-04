const runBtn = document.getElementById('runBtn');
const closeBtn = document.getElementById('closeBtn');
const output = document.getElementById('output');

function showText(text) {
    output.textContent = text;
}

// ---------------- RUN AGENT ----------------
runBtn.addEventListener('click', async () => {
    const prompt = document.getElementById('prompt').value;
    if (!prompt) return alert('Please enter a prompt!');

    showText("Starting agent...\n");

    try {
        const res = await fetch("/run-agent", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt })
        });

        const data = await res.json();

        if (data.status === "success") {
            showText(data.output);
        } else {
            showText("Unexpected response:\n" + JSON.stringify(data, null, 2));
        }
    } catch (err) {
        showText("Error: " + (err.message || err));
    }
});

// ---------------- CLOSE BROWSER ----------------
closeBtn.addEventListener('click', async () => {
    try {
        const res = await fetch("/close-browser", { method: "POST" });
        const data = await res.json();
        showText(data.message || JSON.stringify(data));
    } catch (err) {
        showText("Error: " + (err.message || err));
    }
});
