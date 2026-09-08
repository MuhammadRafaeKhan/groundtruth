import os
import tempfile
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, Response
from geocode import get_coordinates, get_flood_zone, get_hazard_data, generate_report, get_map_image

app = FastAPI()

FAVICON_SVG = """<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
<rect width="64" height="64" rx="14" fill="#1E2A24"/>
<g fill="none" stroke="#F3F4F1" stroke-width="3">
<path d="M14,46 C10,32 20,20 34,18 C48,16 56,26 54,38 C52,50 40,54 28,52 C18,50 16,54 14,46 Z"/>
<path d="M22,42 C20,32 28,24 36,23 C44,22 48,30 46,38 C44,46 34,48 28,46 C22,44 23,46 22,42 Z" opacity="0.75"/>
</g>
<circle cx="33" cy="34" r="4" fill="#A83E32"/>
</svg>"""

@app.get("/favicon.svg")
def favicon():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GroundTruth — Property Climate Risk Reports</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
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
  html { scroll-behavior: smooth; }
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
    position: sticky;
    top: 0;
    z-index: 20;
    background: rgba(243, 244, 241, 0.9);
    backdrop-filter: blur(6px);
    border-bottom: 1px solid transparent;
    transition: border-color 0.25s ease, box-shadow 0.25s ease;
  }
  header.scrolled {
    border-bottom: 1px solid var(--line);
    box-shadow: 0 2px 12px rgba(30, 42, 36, 0.04);
  }
  header .wrap {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 18px;
    padding-bottom: 18px;
  }
  .wordmark {
    font-family: 'Fraunces', serif;
    font-size: 20px;
    font-weight: 600;
    letter-spacing: 0.2px;
    text-decoration: none;
    color: var(--ink);
  }
  .wordmark span { color: var(--teal); }
  nav a {
    position: relative;
    color: var(--ink-soft);
    text-decoration: none;
    font-size: 14px;
    padding-bottom: 3px;
  }
  nav a::after {
    content: "";
    position: absolute;
    left: 0;
    bottom: 0;
    width: 0%;
    height: 1px;
    background: var(--teal);
    transition: width 0.2s ease;
  }
  nav a:hover { color: var(--teal); }
  nav a:hover::after { width: 100%; }

  .hero {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 56px;
    align-items: center;
    padding: 56px 0 72px;
  }
  .fade-up {
    opacity: 0;
    transform: translateY(14px);
    animation: fadeUp 0.6s ease forwards;
  }
  .fade-up.d1 { animation-delay: 0.05s; }
  .fade-up.d2 { animation-delay: 0.15s; }
  .fade-up.d3 { animation-delay: 0.25s; }
  @keyframes fadeUp {
    to { opacity: 1; transform: translateY(0); }
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
    transition: box-shadow 0.25s ease, border-color 0.25s ease;
  }
  .card:hover {
    box-shadow: 0 8px 28px rgba(30, 42, 36, 0.07);
    border-color: #c9cec6;
  }
  .field { margin-bottom: 16px; }
  label {
    display: block;
    font-size: 13px;
    color: var(--ink-soft);
    margin-bottom: 6px;
  }
  input[type="text"] {
    width: 100%;
    padding: 11px 12px;
    border: 1px solid var(--line);
    border-radius: 6px;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 15px;
    color: var(--ink);
    background: var(--paper);
    transition: border-color 0.15s ease, background 0.15s ease;
  }
  input[type="text"]:hover { border-color: #c9cec6; }
  input[type="file"] {
    width: 100%;
    padding: 9px 0;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 14px;
    color: var(--ink-soft);
  }
  input:focus { outline: 2px solid var(--teal); outline-offset: 1px; }
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
    transition: background 0.15s ease, transform 0.1s ease;
  }
  button[type="submit"]:hover { background: #275c4c; transform: translateY(-1px); }
  button[type="submit"]:active { transform: translateY(0); }
  button[type="submit"]:disabled { background: var(--ink-soft); cursor: wait; transform: none; }

  .status {
    margin-top: 12px;
    font-size: 14px;
    color: var(--ink-soft);
    display: none;
  }
  .status.visible { display: block; animation: fadeUp 0.3s ease forwards; }
  .status.error { color: var(--brick); }

  .preview-wrap {
    position: relative;
    height: 720px;
    overflow: hidden;
  }

  .sample-card {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 340px;
    background: #fff;
    border-radius: 14px;
    box-shadow: 0 24px 60px rgba(30, 42, 36, 0.18), 0 6px 16px rgba(30, 42, 36, 0.08);
    overflow: hidden;
    animation: floatCard 6s ease-in-out infinite, dropIn 0.7s ease forwards;
    animation-delay: 0s, 0.3s;
    opacity: 0;
    transform: translate(-50%, calc(-50% + 20px));
    z-index: 3;
  }
  @keyframes dropIn {
    to { opacity: 1; transform: translate(-50%, -50%); }
  }
  @keyframes floatCard {
    0%, 100% { margin-top: 0px; }
    50% { margin-top: -10px; }
  }
  .sample-header {
    background: #1E2A24;
    color: #fff;
    padding: 16px 18px;
    font-family: 'Fraunces', serif;
    font-size: 16px;
    font-weight: 600;
  }
  .sample-body { padding: 18px; }
  .sample-address {
    font-size: 11px;
    color: var(--ink-soft);
    margin-bottom: 12px;
  }
  .sample-badge {
    display: inline-block;
    background: var(--brick);
    color: #fff;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 4px;
    margin-bottom: 16px;
  }
  .sample-row { margin-bottom: 11px; display: flex; align-items: center; gap: 8px; }
  .sample-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .sample-row-inner { flex: 1; }
  .sample-row-label {
    font-size: 10.5px;
    color: var(--ink-soft);
    margin-bottom: 3px;
    display: flex;
    justify-content: space-between;
  }
  .sample-bar-track {
    height: 6px;
    background: #E6E6E0;
    border-radius: 3px;
    overflow: hidden;
  }
  .sample-bar-fill {
    height: 100%;
    width: 0%;
    border-radius: 3px;
    animation: fillBar 1s ease forwards;
  }
  .bar1 { background: var(--brick); animation-delay: 0.9s; }
  .bar2 { background: var(--ochre); animation-delay: 1.0s; }
  .bar3 { background: var(--brick); animation-delay: 1.1s; }
  .bar4 { background: var(--teal); animation-delay: 1.2s; }
  .bar5 { background: var(--teal); animation-delay: 1.3s; }
  @keyframes fillBar {
    to { width: var(--fill); }
  }

  .fact-chip {
    position: absolute;
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 12px 16px;
    box-shadow: 0 10px 26px rgba(30, 42, 36, 0.08);
    max-width: 190px;
    opacity: 0;
    animation: chipIn 0.6s ease forwards;
    z-index: 4;
  }
  .fact-chip .num {
    font-family: 'Fraunces', serif;
    font-size: 22px;
    font-weight: 600;
    color: var(--teal);
    display: block;
  }
  .fact-chip .label {
    font-size: 11.5px;
    color: var(--ink-soft);
    line-height: 1.3;
  }
  .chip1 { top: 4%; left: 2%; animation-delay: 1.6s; animation-name: chipIn, floatChip1; animation-duration: 0.6s, 7s; animation-iteration-count: 1, infinite; animation-timing-function: ease, ease-in-out; }
  .chip2 { bottom: 8%; right: 0%; animation-delay: 1.9s; animation-name: chipIn, floatChip2; animation-duration: 0.6s, 8s; animation-iteration-count: 1, infinite; animation-timing-function: ease, ease-in-out; }
  .chip3 { top: 6%; right: 0%; animation-delay: 2.2s; animation-name: chipIn, floatChip3; animation-duration: 0.6s, 6.5s; animation-iteration-count: 1, infinite; animation-timing-function: ease, ease-in-out; }
  @keyframes chipIn { to { opacity: 1; } }
  @keyframes floatChip1 { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
  @keyframes floatChip2 { 0%,100% { transform: translateY(0); } 50% { transform: translateY(8px); } }
  @keyframes floatChip3 { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }

  .bg-shape {
    position: absolute;
    inset: 0;
    z-index: 1;
  }

  .reveal {
    opacity: 0;
    transform: translateY(16px);
    transition: opacity 0.6s ease, transform 0.6s ease;
  }
  .reveal.in-view { opacity: 1; transform: translateY(0); }

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
  .sources a { color: var(--teal); }

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
    .preview-wrap { height: 560px; }
    .fact-chip { max-width: 150px; padding: 9px 12px; }
  }
</style>
</head>
<body>
<header id="siteHeader">
  <div class="wrap">
    <a href="/" class="wordmark">Ground<span>Truth</span></a>
    <nav><a href="/methodology">Methodology</a></nav>
  </div>
</header>

<div class="wrap">
  <section class="hero">
    <div>
      <h1 class="fade-up d1">Show every buyer the ground truth before they sign.</h1>
      <p class="lede fade-up d2">Enter a property address and get a branded flood, wildfire, and climate risk report — built on FEMA data, ready in under a minute.</p>

      <div class="card fade-up d3">
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
          <div class="field">
            <label for="logo">Your logo (optional)</label>
            <input type="file" id="logo" name="logo" accept="image/png, image/jpeg">
          </div>
          <button type="submit">Generate report</button>
          <div class="status" id="status"></div>
        </form>
      </div>
    </div>

    <div class="preview-wrap fade-up d2">
      <svg class="bg-shape" viewBox="0 0 400 720" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
        <g fill="none" stroke="#2F6E5B" stroke-width="1.2" opacity="0.35">
          <path d="M40,600 C20,480 90,360 200,330 C310,300 380,380 360,480 C340,580 260,620 160,610 C80,602 60,650 40,600 Z"/>
          <path d="M80,560 C65,460 120,370 200,350 C280,330 330,390 315,460 C300,530 240,555 180,545 C130,537 100,585 80,560 Z" opacity="0.7"/>
        </g>
      </svg>

      <div class="fact-chip chip1">
        <span class="num">5</span>
        <span class="label">Live FEMA data sources in every report</span>
      </div>
      <div class="fact-chip chip2">
        <span class="num">50</span>
        <span class="label">States covered, coast to coast</span>
      </div>
      <div class="fact-chip chip3">
        <span class="num">&lt;1min</span>
        <span class="label">From address to finished PDF</span>
      </div>

      <div class="sample-card">
        <div class="sample-header">GroundTruth</div>
        <div class="sample-body">
          <div class="sample-address">412 River Bend Rd, Sample City, FL</div>
          <span class="sample-badge">High Risk</span>

          <div class="sample-row">
            <span class="sample-dot" style="background: var(--brick);"></span>
            <div class="sample-row-inner">
              <div class="sample-row-label"><span>Flood</span><span>Zone AE</span></div>
              <div class="sample-bar-track"><div class="sample-bar-fill bar1" style="--fill: 82%;"></div></div>
            </div>
          </div>
          <div class="sample-row">
            <span class="sample-dot" style="background: var(--ochre);"></span>
            <div class="sample-row-inner">
              <div class="sample-row-label"><span>Hurricane</span><span>Relatively High</span></div>
              <div class="sample-bar-track"><div class="sample-bar-fill bar2" style="--fill: 68%;"></div></div>
            </div>
          </div>
          <div class="sample-row">
            <span class="sample-dot" style="background: var(--brick);"></span>
            <div class="sample-row-inner">
              <div class="sample-row-label"><span>Heat Wave</span><span>Very High</span></div>
              <div class="sample-bar-track"><div class="sample-bar-fill bar3" style="--fill: 90%;"></div></div>
            </div>
          </div>
          <div class="sample-row">
            <span class="sample-dot" style="background: var(--teal);"></span>
            <div class="sample-row-inner">
              <div class="sample-row-label"><span>Wildfire</span><span>Relatively Low</span></div>
              <div class="sample-bar-track"><div class="sample-bar-fill bar4" style="--fill: 24%;"></div></div>
            </div>
          </div>
          <div class="sample-row">
            <span class="sample-dot" style="background: var(--teal);"></span>
            <div class="sample-row-inner">
              <div class="sample-row-label"><span>Tornado</span><span>Very Low</span></div>
              <div class="sample-bar-track"><div class="sample-bar-fill bar5" style="--fill: 12%;"></div></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="steps reveal">
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

  <section class="sources reveal">
    <strong>Where the data comes from.</strong> Flood zone data is pulled directly from FEMA's National Flood Hazard Layer. Wildfire, heat wave, drought, hurricane, and tornado risk come from FEMA's National Risk Index. See our full <a href="/methodology">methodology page</a> for exact sources and calculations.
  </section>
</div>

<footer>
  <div class="wrap">
    This tool is for informational purposes only and is not a substitute for a professional inspection, insurance consultation, or official flood determination.
  </div>
</footer>

<script>
const header = document.getElementById('siteHeader');
window.addEventListener('scroll', function () {
  if (window.scrollY > 8) {
    header.classList.add('scrolled');
  } else {
    header.classList.remove('scrolled');
  }
});

const revealEls = document.querySelectorAll('.reveal');
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('in-view');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });
revealEls.forEach(el => observer.observe(el));

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

@app.get("/methodology", response_class=HTMLResponse)
def methodology():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Methodology — GroundTruth</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --paper: #F3F4F1; --ink: #1E2A24; --ink-soft: #4B5A52; --line: #D8DBD3; --teal: #2F6E5B;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--paper); color: var(--ink); font-family: 'IBM Plex Sans', sans-serif; line-height: 1.6; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 0 28px 60px; }
  header { padding: 28px 0; }
  .wordmark { font-family: 'Fraunces', serif; font-size: 20px; font-weight: 600; text-decoration: none; color: var(--ink); }
  .wordmark span { color: var(--teal); }
  h1 { font-family: 'Fraunces', serif; font-size: 34px; font-weight: 500; margin: 20px 0 8px; }
  .updated { color: var(--ink-soft); font-size: 14px; margin-bottom: 40px; }
  h2 { font-family: 'Fraunces', serif; font-size: 21px; font-weight: 500; margin: 40px 0 10px; }
  p { color: var(--ink-soft); font-size: 16px; margin: 0 0 12px; }
  .source-box {
    background: #fff; border: 1px solid var(--line); border-radius: 8px;
    padding: 16px 20px; margin: 14px 0; transition: box-shadow 0.2s ease;
  }
  .source-box:hover { box-shadow: 0 6px 20px rgba(30, 42, 36, 0.06); }
  .source-box strong { color: var(--ink); }
  a { color: var(--teal); }
  .back { display: inline-block; margin-top: 40px; color: var(--teal); text-decoration: none; font-size: 14px; }
</style>
</head>
<body>
<header>
  <div class="wrap">
    <a href="/" class="wordmark">Ground<span>Truth</span></a>
  </div>
</header>
<div class="wrap">
  <h1>Methodology</h1>
  <p class="updated">How every number in a GroundTruth report is sourced and calculated.</p>

  <h2>Flood zone</h2>
  <div class="source-box">
    <strong>Source:</strong> FEMA National Flood Hazard Layer (NFHL)<br>
    We query FEMA's live flood hazard database for the exact coordinates of the address entered. The zone returned (such as X, A, or AE) is FEMA's official flood designation for that specific point.
  </div>

  <h2>Wildfire, heat wave, drought, hurricane, and tornado risk</h2>
  <div class="source-box">
    <strong>Source:</strong> FEMA National Risk Index (county level)<br>
    Each rating (Very Low through Very High) and each national percentile score reflects the entire county the address falls in, not the individual property. This is the same dataset FEMA publishes for emergency planners and researchers nationwide.
  </div>

  <h2>Flood insurance cost context</h2>
  <div class="source-box">
    <strong>Source:</strong> FEMA National Flood Insurance Program (NFIP) policy data, July 2026 snapshot<br>
    The dollar figure shown is the average annual NFIP payment across all existing policies in that state. It is not a personalized quote — actual premiums depend on coverage amount, deductible, elevation, and foundation type, which require an official insurance consultation to determine.
  </div>

  <h2>Flood disaster history</h2>
  <div class="source-box">
    <strong>Source:</strong> FEMA OpenFEMA Disaster Declarations Summary<br>
    We count federally declared flood disasters for the property's county since 2000, using FEMA's public disaster declarations database, which records every federal disaster declaration since 1953.
  </div>

  <h2>What this tool does not do</h2>
  <p>GroundTruth does not perform a property-level inspection, does not replace an official flood determination, and does not issue insurance quotes. All figures are informational and intended to support, not replace, professional advice from a licensed inspector, insurance agent, or flood zone specialist.</p>

  <a href="/" class="back">&larr; Back to GroundTruth</a>
</div>
</body>
</html>
    """

@app.post("/generate")
def generate(
    address: str = Form(...),
    agent_name: str = Form(...),
    agent_contact: str = Form(...),
    logo: UploadFile = File(None)
):
    result = get_coordinates(address)
    if not result:
        return HTMLResponse("<p>Could not find that address. <a href='/'>Try again</a></p>", status_code=400)

    flood = get_flood_zone(result["latitude"], result["longitude"])
    hazard = get_hazard_data(result["latitude"], result["longitude"])
    filename = "risk_report.pdf"

    logo_path = None
    if logo is not None and logo.filename:
        suffix = os.path.splitext(logo.filename)[1] or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(logo.file.read())
            logo_path = tmp.name

    map_path = get_map_image(result["latitude"], result["longitude"], tempfile.mktemp(suffix=".png"))

    generate_report(result, flood, hazard, agent_name, agent_contact, filename, logo_path=logo_path, map_path=map_path)

    if logo_path and os.path.exists(logo_path):
        os.remove(logo_path)
    if map_path and os.path.exists(map_path):
        os.remove(map_path)

    return FileResponse(filename, filename="risk_report.pdf", media_type="application/pdf")