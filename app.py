from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse
from geocode import get_coordinates, get_flood_zone, get_hazard_data, generate_report

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head><title>Property Risk Report</title></head>
    <body style="font-family: sans-serif; max-width: 500px; margin: 50px auto;">
        <h2>Generate a Property Risk Report</h2>
        <form action="/generate" method="post">
            <label>Property Address:</label><br>
            <input type="text" name="address" style="width:100%; padding:8px;" required><br><br>
            <label>Your Name (Agent):</label><br>
            <input type="text" name="agent_name" style="width:100%; padding:8px;" required><br><br>
            <label>Your Contact Info:</label><br>
            <input type="text" name="agent_contact" style="width:100%; padding:8px;" required><br><br>
            <button type="submit" style="padding:10px 20px;">Generate Report</button>
        </form>
    </body>
    </html>
    """

@app.post("/generate")
def generate(address: str = Form(...), agent_name: str = Form(...), agent_contact: str = Form(...)):
    result = get_coordinates(address)
    if not result:
        return HTMLResponse("<p>Could not find that address. <a href='/'>Try again</a></p>")

    flood = get_flood_zone(result["latitude"], result["longitude"])
    hazard = get_hazard_data(result["latitude"], result["longitude"])
    filename = "risk_report.pdf"
    generate_report(result, flood, hazard, agent_name, agent_contact, filename)

    return FileResponse(filename, filename="risk_report.pdf", media_type="application/pdf")