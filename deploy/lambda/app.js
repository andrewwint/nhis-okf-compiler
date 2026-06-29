// Page and API share one origin (the Lambda Function URL), so POST to the same path.
const API_URL = window.location.href.split("?")[0];

const log = document.getElementById("log");
const form = document.getElementById("f");
const input = document.getElementById("q");

function add(text, cls) {
  const div = document.createElement("div");
  div.className = "msg " + cls;
  div.textContent = text;
  log.appendChild(div);
  div.scrollIntoView({ behavior: "smooth" });
  return div;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;
  add(q, "you");
  input.value = "";
  const pending = add("…", "bot");
  try {
    const r = await fetch(API_URL, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    const data = await r.json();
    pending.textContent = data.answer || data.error || "(no answer)";
  } catch (err) {
    pending.textContent = "Request failed: " + err;
  }
});
