const runBtn = document.getElementById("runBtn");
const closeBtn = document.getElementById("closeBtn");
const output = document.getElementById("output");

function show(message) {
    output.textContent = message;
}

// ---------------- RUN AGENT ----------------
runBtn.addEventListener("click", async () => {
    const prompt = document.getElementById("prompt").value.trim();

    if (!prompt) {
        alert("Please enter a prompt!");
        return;
    }

    show("⚙️ Running agent... Please wait...");

    try {
        const response = await fetch("/run-agent", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt }),
        });

        const rawText = await response.text(); // get raw response

        let data;

        try {
            data = JSON.parse(rawText); // convert to JSON
        } catch (err) {
            show("❌ Backend returned invalid JSON:\n\n" + rawText);
            return;
        }

        // SUCCESS CASE
        if (data.status === "success") {
            show("✅ Agent Output:\n\n" + data.output);
        } else {
            // ERROR CASE
            show("❌ Error:\n\n" + (data.output || "Unknown backend error"));
        }

    } catch (error) {
        show("❌ Network Error:\n" + error.message);
    }
});

// ---------------- CLOSE BROWSER ----------------
closeBtn.addEventListener("click", async () => {
    show("🛑 Closing browser...");

    try {
        const response = await fetch("/close-browser", {
            method: "POST",
        });

        const rawText = await response.text();
        let data;

        try {
            data = JSON.parse(rawText);
        } catch (err) {
            show("❌ Backend returned invalid JSON:\n\n" + rawText);
            return;
        }

        if (data.message) {
            show("🛑 " + data.message);
        } else {
            show("⚠️ Unknown backend response");
        }
    } catch (error) {
        show("❌ Network Error:\n" + error.message);
    }
});
