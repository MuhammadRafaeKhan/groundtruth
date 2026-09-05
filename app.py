from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse
from geocode import get_coordinates, get_flood_zone, get_hazard_data, generate_report

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GroundTruth — Property Climate Risk Reports</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --paper: #F3F4F1;
    --ink: #1E2A24;
    --ink-soft: #4B5A52;
    --line: #D8DBD3;
    --teal: #2F6E5B;
    --ochre: #C08A2E;
    --brick: #A83E32;
    --card: #FFFFFF;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: 'IBM Plex Sans', sans-serif;
    line-height: 1.5;
  }
  h1, h2 {
    font-family: 'Fraunces', serif;
    font-weight: 500;
    line-height: 1.15;
    margin: 0;
  }
  .wrap { max-width: 1080px; margin: 0 auto; padding: 0 28px; }
  header {
    padding: 28px 0 0;
  }
  .wordmark {
    font-family: 'Fraunces', serif;
    font-size: 20px;
    font-weight: 600;
    letter-spacing: 0.2px;
  }
  .wordmark span { color: var(--teal); }

  .hero {
    display: grid;
    grid-template-columns: 1.1fr 0.9fr;
    gap: 56px;
    align-items: center;
    padding: 56px 0 72px;
  }
  .hero h1 { font-size: 42px; max-width: 480px; }
  .hero p.lede {
    max-width: 440px;
    color: var(--ink-soft);
    font-size: 17px;
    margin-top: 18px;
  }

  .card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 28px;
    margin-top: 32px;
  }
  .field { margin-bottom: 16px; }
  label {
    display: block;
    font-size: 13px;
    color: var(--ink-soft);
    margin-bottom: 6px;
  }
  input {
    width: 100%;
    padding: 11px 12px;
    border: 1px solid var(--line);
    border-radius: 6px;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 15px;
    color: var(--ink);
    background: var(--paper);
  }
  input:focus {
    outline: 2px solid var(--teal);
    outline-offset: 1px;
  }
  button[type="submit"] {
    width: 100%;
    padding: 13px;
    background: var(--teal);
    color: #fff;
    border: none;
    border-radius: 6px;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
    margin-top: 4px;
    transition: background 0.15s ease;
  }
  button[type="submit"]:hover { background: #275c4c; }
  button[type="submit"]:disabled { background: var(--ink-soft); cursor: wait; }

  .status {
    margin-top: 12px;
    font-size: 14px;
    color: var(--ink-soft);
    display: none;
  }
  .status.visible { display: block; }
  .status.error { color: var(--brick); }

  .contour {
    width: 100%;
    height: auto;
  }

  .steps {
    border-top: 1px solid var(--line);
    padding: 56px 0;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 40px;
  }
  .step .num {
    font-family: 'Fraunces', serif;
    font-size: 15px;
    color: var(--teal);
    border-bottom: 2px solid var(--teal);
    display: inline-block;
    padding-bottom: 4px;
    margin-bottom: 14px;
  }
  .step h2 { font-size: 19px; }
  .step p { color: var(--ink-soft); font-size: 15px; margin-top: 8px; }

  .sources {
    border-top: 1px solid var(--line);
    padding: 40px 0;
    color: var(--ink-soft);
    font-size: 14px;
  }
  .sources strong { color: var(--ink); }

  footer {
    border-top: 1px solid var(--line);
    padding: 28px 0 40px;
    color: var(--ink-soft);
    font-size: 13px;
  }

  @media (max-width: 800px) {
    .hero { grid-template-columns: 1fr; }
    .steps { grid-template-columns: 1fr; }
    .hero h1 { font-size: 32px; }
  }
</style>
</head>
<body>
<header>
  <div class="wrap">
    <div class="wordmark">Ground<span>Truth</span></div>
  </div>
</header>

<div class="wrap">
  <section class="hero">
    <div>
      <h1>Show every buyer the ground truth before they sign.</h1>
      <p class="lede">Enter a property address and get a branded flood, wildfire, and climate risk report — built on FEMA data, ready in under a minute.</p>

      <div class="card">
        <form id="reportForm">
          <div class="field">
            <label for="address">Property address</label>
            <input type="text" id="address" name="address" placeholder="123 Main St, City, State" required>
          </div>
          <div class="field">
            <label for="agent_name">Your name</label>
            <input type="text" id="agent_name" name="agent_name" placeholder="Jane Smith" required>
          </div>
          <div class="field">
            <label for="agent_contact">Your contact info</label>
            <input type="text" id="agent_contact" name="agent_contact" placeholder="jane@example.com" required>
          </div>
          <button type="submit">Generate report</button>
          <div class="status" id="status"></div>
        </form>
      </div>
    </div>

    <div>
      <svg class="contour" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
        <g fill="none" stroke="#2F6E5B" stroke-width="1.2" opacity="0.5">
          <path d="M60,340 C40,260 90,180 180,160 C270,140 340,190 350,270 C358,340 300,380 220,370 C140,362 80,400 60,340 Z"/>
          <path d="M90,320 C75,255 115,195 185,180 C255,165 310,205 318,265 C325,320 280,350 215,345 C155,340 105,365 90,320 Z" opacity="0.7"/>
          <path d="M120,300 C110,250 140,205 190,195 C240,185 280,215 285,260 C290,300 255,325 205,320 C160,316 128,335 120,300 Z" opacity="0.85"/>
          <path d="M150,280 C145,245 165,215 195,208 C225,201 250,220 253,250 C256,280 235,295 205,292 C177,289 154,303 150,280 Z" opacity="1"/>
        </g>
        <circle cx="200" cy="248" r="4" fill="#A83E32"/>
      </svg>
    </div>
  </section>

  <section class="steps">
    <div class="step">
      <span class="num">1</span>
      <h2>Enter the address</h2>
      <p>Any US property address — residential, commercial, or a listing you're prepping.</p>
    </div>
    <div class="step">
      <span class="num">2</span>
      <h2>We pull the data</h2>
      <p>Live FEMA flood zone lookup, plus county-level wildfire, heat, drought, hurricane, and tornado risk.</p>
    </div>
    <div class="step">
      <span class="num">3</span>
      <h2>Send the report</h2>
      <p>A clean, branded PDF with your name and contact info — ready to hand to your client.</p>
    </div>
  </section>

  <section class="sources">
    <strong>Where the data comes from.</strong> Flood zone data is pulled directly from FEMA's National Flood Hazard Layer. Wildfire, heat wave, drought, hurricane, and tornado risk come from FEMA's National Risk Index — the same federal data used by insurers and emergency planners nationwide.
  </section>
</div>

<footer>
  <div class="wrap">
    This tool is for informational purposes only and is not a substitute for a professional inspection, insurance consultation, or official flood determination.
  </div>
</footer>

<script>
document.getElementById('reportForm').addEventListener('submit', async function (e) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');
  const status = document.getElementById('status');
  const originalText = btn.textContent;

  btn.disabled = true;
  btn.textContent = 'Generating report…';
  status.className = 'status visible';
  status.textContent = 'Looking up flood and hazard data for this address…';

  try {
    const formData = new FormData(form);
    const res = await fetch('/generate', { method: 'POST', body: formData });
    if (!res.ok) throw new Error('Request failed');

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'risk_report.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    status.textContent = 'Report downloaded.';
  } catch (err) {
    status.className = 'status visible error';
    status.textContent = 'Could not generate a report for that address. Please check it and try again.';
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
});
</script>
</body>
</html>
    """

@app.post("/generate")
def generate(address: str = Form(...), agent_name: str = Form(...), agent_contact: str = Form(...)):
    result = get_coordinates(address)
    if not result:
        return HTMLResponse("<p>Could not find that address. <a href='/'>Try again</a></p>", status_code=400)

    flood = get_flood_zone(result["latitude"], result["longitude"])
    hazard = get_hazard_data(result["latitude"], result["longitude"])
    filename = "risk_report.pdf"
    generate_report(result, flood, hazard, agent_name, agent_contact, filename)

    return FileResponse(filename, filename="risk_report.pdf", media_type="application/pdf")