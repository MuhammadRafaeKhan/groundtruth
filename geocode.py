import requests
import os
from fpdf import FPDF
from staticmap import StaticMap, CircleMarker

STATE_NFIP_AVERAGES = {
    "WV": 2260, "VT": 2126, "PA": 1895, "CT": 1874, "MO": 1837, "KY": 1811,
    "ME": 1770, "IA": 1694, "TN": 1553, "NH": 1537, "SD": 1536, "MA": 1536,
    "NY": 1522, "MS": 1517, "NM": 1488, "MN": 1431, "RI": 1412, "NJ": 1406,
    "OH": 1396, "OK": 1387, "AR": 1372, "KS": 1352, "WA": 1319, "IL": 1305,
    "LA": 1292, "CA": 1291, "IN": 1289, "ID": 1282, "NE": 1280, "WY": 1270,
    "CO": 1253, "OR": 1248, "WI": 1244, "TX": 1234, "MT": 1219, "AL": 1185,
    "NC": 1179, "NV": 1175, "FL": 1169, "GA": 1134, "AZ": 1110, "ND": 1104,
    "DE": 1093, "MI": 1077, "HI": 987, "VA": 977, "SC": 973, "UT": 882,
    "MD": 653, "AK": 588
}
NATIONAL_NFIP_AVERAGE = 1233

def get_coordinates(address):
    url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
    params = {
        "address": address,
        "benchmark": "Public_AR_Current",
        "format": "json"
    }
    response = requests.get(url, params=params)
    data = response.json()
    matches = data["result"]["addressMatches"]
    if not matches:
        return None
    coords = matches[0]["coordinates"]
    return {
        "latitude": coords["y"],
        "longitude": coords["x"],
        "matched_address": matches[0]["matchedAddress"]
    }

def get_flood_zone(lat, lon):
    url = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "FLD_ZONE,ZONE_SUBTY",
        "returnGeometry": "false",
        "f": "json"
    }
    response = requests.get(url, params=params)
    data = response.json()
    features = data.get("features", [])
    if not features:
        return {"zone": "Unknown"}
    zone = features[0]["attributes"]["FLD_ZONE"]
    return {"zone": zone}

def get_hazard_data(lat, lon):
    url = "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0/query"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "COUNTY,STATE,STCOFIPS,WFIR_RISKR,WFIR_RISKS,HWAV_RISKR,HWAV_RISKS,DRGT_RISKR,DRGT_RISKS,HRCN_RISKR,HRCN_RISKS,TRND_RISKR,TRND_RISKS,RISK_SCORE",
        "returnGeometry": "false",
        "f": "json"
    }
    response = requests.get(url, params=params)
    data = response.json()
    features = data.get("features", [])
    if not features:
        return None
    return features[0]["attributes"]

def get_map_image(lat, lon, output_path):
    try:
        m = StaticMap(500, 300, url_template='https://a.tile.openstreetmap.org/{z}/{x}/{y}.png')
        marker = CircleMarker((lon, lat), '#A83E32', 14)
        m.add_marker(marker)
        image = m.render(zoom=15)
        image.save(output_path)
        return output_path
    except Exception:
        return None

def get_disaster_history(stcofips, incident_type="Flood", since_year=2000):
    if not stcofips or len(stcofips) < 5:
        return None
    state_fips = stcofips[:2]
    county_fips = stcofips[2:]
    url = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
    filter_str = (
        f"fipsStateCode eq '{state_fips}' and fipsCountyCode eq '{county_fips}' "
        f"and incidentType eq '{incident_type}' "
        f"and declarationDate ge '{since_year}-01-01T00:00:00.000Z'"
    )
    params = {
        "$filter": filter_str,
        "$select": "disasterNumber,declarationTitle,incidentBeginDate,declarationDate",
        "$orderby": "declarationDate desc",
        "$format": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        records = data.get("DisasterDeclarationsSummaries", [])
        seen = set()
        events = []
        for r in records:
            num = r.get("disasterNumber")
            if num in seen:
                continue
            seen.add(num)
            year = r.get("declarationDate", "")[:4]
            events.append({"year": year, "title": r.get("declarationTitle", "").title()})
        return events
    except Exception:
        return None

def get_state_abbrev(matched_address):
    parts = matched_address.split(",")
    if len(parts) >= 2:
        return parts[-2].strip()
    return ""

def get_insurance_estimate(matched_address):
    state = get_state_abbrev(matched_address)
    avg = STATE_NFIP_AVERAGES.get(state, NATIONAL_NFIP_AVERAGE)
    return {"state": state, "average_annual": avg}

def get_highest_percentile(hazard_data):
    if not hazard_data:
        return None
    score_fields = {
        "Wildfire": "WFIR_RISKS",
        "Heat Wave": "HWAV_RISKS",
        "Drought": "DRGT_RISKS",
        "Hurricane": "HRCN_RISKS",
        "Tornado": "TRND_RISKS"
    }
    best = None
    for name, field in score_fields.items():
        val = hazard_data.get(field)
        try:
            val = float(val)
        except (TypeError, ValueError):
            continue
        if best is None or val > best[1]:
            best = (name, val)
    return best

def explain_flood_zone(zone):
    high_risk_zones = ["A", "AE", "AH", "AO", "AR", "A99", "V", "VE"]
    if zone in high_risk_zones:
        return f"This property is in FEMA Flood Zone {zone}, a high-risk flood area. Flood insurance is typically required by mortgage lenders for properties in this zone."
    elif zone == "X":
        return "This property is in FEMA Flood Zone X, a lower-risk flood area. Flood insurance is usually optional here, though flooding can still occur."
    else:
        return f"Flood zone data for this property is listed as '{zone}'. Consult a flood zone specialist for full details."

HAZARD_EXPLANATIONS = {
    "Wildfire": "Reflects this county's likelihood of destructive wildfire activity, based on historical fire data and vegetation conditions.",
    "Heat Wave": "Reflects how often and how severely this county experiences extreme, prolonged heat events.",
    "Drought": "Reflects this county's exposure to prolonged water shortages, which can affect property value, landscaping, and water costs.",
    "Hurricane": "Reflects this county's exposure to hurricane-force winds and related storm damage.",
    "Tornado": "Reflects the historical frequency and severity of tornado activity recorded in this county."
}

def risk_score(rating):
    mapping = {
        "Very Low": 1, "Relatively Low": 2, "Relatively Moderate": 3,
        "Relatively High": 4, "Very High": 5, "Not Applicable": 0,
        "No Rating": 0, "Insufficient Data": 0
    }
    return mapping.get(rating, 2)

def flood_score(zone):
    high_risk_zones = ["A", "AE", "AH", "AO", "AR", "A99", "V", "VE"]
    if zone in high_risk_zones:
        return 4
    elif zone == "X":
        return 1
    else:
        return 2

def risk_color(score):
    if score == 0:
        return (190, 190, 185)
    elif score <= 2:
        return (47, 110, 91)
    elif score == 3:
        return (192, 138, 46)
    else:
        return (168, 62, 50)

def overall_risk_level(flood_zone, hazard_data):
    scores = [flood_score(flood_zone)]
    if hazard_data:
        for key in ["WFIR_RISKR", "HWAV_RISKR", "DRGT_RISKR", "HRCN_RISKR", "TRND_RISKR"]:
            scores.append(risk_score(hazard_data.get(key, "")))
    high_count = sum(1 for s in scores if s >= 4)
    if high_count >= 2:
        return "High"
    elif high_count == 1:
        return "Medium"
    else:
        return "Low"

def draw_risk_row(pdf, label, rating_text, score, y):
    left_margin = 15
    pdf.set_xy(left_margin, y)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 40, 35)
    pdf.cell(42, 7, label)

    bar_x = left_margin + 44
    bar_width = 85
    bar_height = 6

    pdf.set_fill_color(230, 230, 224)
    pdf.rect(bar_x, y + 1, bar_width, bar_height, 'F')

    r, g, b = risk_color(score)
    fill_width = max(bar_width * (score / 5), 3) if score > 0 else 3
    pdf.set_fill_color(r, g, b)
    pdf.rect(bar_x, y + 1, fill_width, bar_height, 'F')

    pdf.set_xy(bar_x + bar_width + 5, y)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(75, 90, 82)
    pdf.cell(45, 7, rating_text)

def draw_legend(pdf, y):
    left_margin = 15
    labels = ["Very Low", "Low", "Moderate", "High", "Very High"]
    colors = [risk_color(1), risk_color(1), risk_color(3), risk_color(4), risk_color(5)]
    box_w = 34
    pdf.set_font("Helvetica", "", 8)
    for i, (label, color) in enumerate(zip(labels, colors)):
        x = left_margin + (i * box_w)
        r, g, b = color
        pdf.set_fill_color(r, g, b)
        pdf.rect(x, y, box_w - 2, 4, 'F')
        pdf.set_xy(x, y + 5)
        pdf.set_text_color(75, 90, 82)
        pdf.cell(box_w - 2, 4, label, align="C")

def generate_report(address_data, flood_data, hazard_data, agent_name, agent_contact, output_filename, logo_path=None, map_path=None):
    overall = overall_risk_level(flood_data["zone"], hazard_data)
    overall_colors = {"Low": (47, 110, 91), "Medium": (192, 138, 46), "High": (168, 62, 50)}
    insurance = get_insurance_estimate(address_data["matched_address"])
    stcofips = hazard_data.get("STCOFIPS", "") if hazard_data else ""
    disaster_history = get_disaster_history(stcofips)
    top_percentile = get_highest_percentile(hazard_data)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_fill_color(30, 42, 36)
    pdf.rect(0, 0, 210, 30, 'F')
    pdf.set_xy(15, 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "GroundTruth")
    pdf.set_xy(15, 19)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Property Climate Risk Report")

    if logo_path:
        try:
            pdf.image(logo_path, x=170, y=6, w=25)
        except Exception:
            pass

    y = 42
    pdf.set_text_color(30, 40, 35)
    pdf.set_xy(15, y)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"Prepared by {agent_name}  |  {agent_contact}")
    y += 10

    pdf.set_xy(15, y)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, "Property Address")
    y += 7
    pdf.set_xy(15, y)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(180, 6, address_data["matched_address"])
    y = pdf.get_y() + 6

    if map_path:
        try:
            pdf.image(map_path, x=15, y=y, w=180, h=55)
            y += 61
        except Exception:
            pass

    r, g, b = overall_colors[overall]
    pdf.set_fill_color(r, g, b)
    pdf.rect(15, y, 55, 16, 'F')
    pdf.set_xy(15, y + 4)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(55, 8, f"{overall} Risk", align="C")
    pdf.set_text_color(30, 40, 35)

    if top_percentile:
        name, pct = top_percentile
        pdf.set_xy(75, y + 2)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(75, 90, 82)
        pdf.multi_cell(120, 5, f"{name} risk here ranks higher than {pct:.0f}% of US counties (FEMA National Risk Index).")

    y += 26

    pdf.set_xy(15, y)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 40, 35)
    pdf.cell(0, 7, "Risk Index")
    y += 9

    draw_legend(pdf, y)
    y += 13

    draw_risk_row(pdf, "Flood", flood_data["zone"], flood_score(flood_data["zone"]), y)
    y += 11

    hazard_scores = {}
    if hazard_data:
        labels = {
            "WFIR_RISKR": "Wildfire", "HWAV_RISKR": "Heat Wave", "DRGT_RISKR": "Drought",
            "HRCN_RISKR": "Hurricane", "TRND_RISKR": "Tornado"
        }
        for key, name in labels.items():
            rating = hazard_data.get(key, "Unknown")
            score = risk_score(rating)
            hazard_scores[name] = rating
            display_text = "N/A" if rating == "Not Applicable" else rating
            draw_risk_row(pdf, name, display_text, score, y)
            y += 11
    else:
        pdf.set_xy(15, y)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 6, "County-level hazard data unavailable for this location.")
        y += 11

    if y > 240:
        pdf.add_page()
        y = 20

    y += 8
    pdf.set_fill_color(240, 240, 235)
    pdf.rect(15, y, 180, 34, 'F')
    pdf.set_xy(20, y + 4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 40, 35)
    pdf.cell(0, 6, f"Flood insurance context: {insurance['state']} state average")
    pdf.set_xy(20, y + 13)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(47, 110, 91)
    pdf.cell(0, 8, f"${insurance['average_annual']:,} / year")
    pdf.set_xy(70, y + 13)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(75, 90, 82)
    pdf.multi_cell(120, 4.5, "Average annual NFIP payment across all policies in this state (FEMA, July 2026). Not a quote for this specific property - actual cost depends on coverage amount, elevation, and foundation type.")
    y += 40

    if y > 235:
        pdf.add_page()
        y = 20

    county_name = hazard_data.get("COUNTY", "this county") if hazard_data else "this county"
    box_height = 24
    if disaster_history:
        box_height = 24 + (min(len(disaster_history), 4) * 5)

    pdf.set_fill_color(240, 240, 235)
    pdf.rect(15, y, 180, box_height, 'F')
    pdf.set_xy(20, y + 4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 40, 35)
    pdf.cell(0, 6, f"Flood history: {county_name} County, FEMA declarations since 2000")
    inner_y = y + 12
    if disaster_history is None:
        pdf.set_xy(20, inner_y)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(75, 90, 82)
        pdf.cell(0, 5, "Historical disaster data temporarily unavailable.")
    elif len(disaster_history) == 0:
        pdf.set_xy(20, inner_y)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(75, 90, 82)
        pdf.cell(0, 5, "No FEMA-declared flood disasters recorded for this county since 2000.")
    else:
        pdf.set_xy(20, inner_y)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(47, 110, 91)
        pdf.cell(0, 5, f"{len(disaster_history)} FEMA-declared flood disaster(s) since 2000")
        inner_y += 6
        for event in disaster_history[:4]:
            pdf.set_xy(20, inner_y)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(75, 90, 82)
            pdf.cell(0, 5, f"{event['year']} - {event['title']}")
            inner_y += 5
    y += box_height + 8

    if y > 235:
        pdf.add_page()
        y = 20

    pdf.set_xy(15, y)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 40, 35)
    pdf.cell(0, 6, "What this means")
    y += 8

    pdf.set_xy(15, y)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 40, 35)
    pdf.cell(0, 5, "Flood")
    y += 5
    pdf.set_xy(15, y)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(75, 90, 82)
    pdf.multi_cell(180, 5, explain_flood_zone(flood_data["zone"]))
    y = pdf.get_y() + 4

    for name, rating in hazard_scores.items():
        if y > 255:
            pdf.add_page()
            y = 20
        pdf.set_xy(15, y)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(30, 40, 35)
        pdf.cell(0, 5, name)
        y += 5
        pdf.set_xy(15, y)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(75, 90, 82)
        pdf.multi_cell(180, 5, HAZARD_EXPLANATIONS.get(name, ""))
        y = pdf.get_y() + 4

    y += 4
    pdf.set_xy(15, y)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(180, 5, "Disclaimer: This report is for informational purposes only and is not a substitute for a professional inspection, insurance consultation, or official flood determination. Flood data sourced from FEMA NFHL. Other hazard data and national percentile rankings sourced from FEMA's National Risk Index at the county level. Insurance figures are state averages from FEMA NFIP policy data (July 2026). Flood history sourced from FEMA's OpenFEMA Disaster Declarations database.")

    pdf.output(output_filename)
    print(f"Report saved as: {output_filename}")

if __name__ == "__main__":
    address = input("Enter an address: ")
    agent_name = input("Enter agent name: ")
    agent_contact = input("Enter agent contact info: ")

    result = get_coordinates(address)
    if result:
        flood = get_flood_zone(result["latitude"], result["longitude"])
        hazard = get_hazard_data(result["latitude"], result["longitude"])
        map_path = get_map_image(result["latitude"], result["longitude"], "map_temp.png")
        generate_report(result, flood, hazard, agent_name, agent_contact, "risk_report.pdf", map_path=map_path)
        if map_path and os.path.exists(map_path):
            os.remove(map_path)
    else:
        print("Could not find that address.")