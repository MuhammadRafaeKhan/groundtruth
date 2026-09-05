import requests
from fpdf import FPDF

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
        "outFields": "COUNTY,STATE,WFIR_RISKR,HWAV_RISKR,DRGT_RISKR,HRCN_RISKR,TRND_RISKR",
        "returnGeometry": "false",
        "f": "json"
    }
    response = requests.get(url, params=params)
    data = response.json()
    features = data.get("features", [])
    if not features:
        return None
    return features[0]["attributes"]

def explain_flood_zone(zone):
    high_risk_zones = ["A", "AE", "AH", "AO", "AR", "A99", "V", "VE"]
    if zone in high_risk_zones:
        return f"This property is in FEMA Flood Zone {zone}, a high-risk flood area. Flood insurance is typically required by mortgage lenders for properties in this zone."
    elif zone == "X":
        return "This property is in FEMA Flood Zone X, a lower-risk flood area. Flood insurance is usually optional here, though flooding can still occur."
    else:
        return f"Flood zone data for this property is listed as '{zone}'. Consult a flood zone specialist for full details."

def is_high(rating):
    return rating in ["Relatively High", "Very High"]

def build_hazard_text(hazard_data):
    if not hazard_data:
        return "Hazard data unavailable for this location."
    lines = []
    labels = {
        "WFIR_RISKR": "Wildfire",
        "HWAV_RISKR": "Heat Wave",
        "DRGT_RISKR": "Drought",
        "HRCN_RISKR": "Hurricane",
        "TRND_RISKR": "Tornado"
    }
    for key, name in labels.items():
        rating = hazard_data.get(key, "Unknown")
        if rating == "Not Applicable":
            lines.append(f"{name} Risk: Not applicable for this county.")
        else:
            lines.append(f"{name} Risk: {rating}")
    return "\n".join(lines)

def overall_risk_level(flood_zone, hazard_data):
    high_flood = flood_zone in ["A", "AE", "AH", "AO", "AR", "A99", "V", "VE"]
    high_count = 0
    if hazard_data:
        for key in ["WFIR_RISKR", "HWAV_RISKR", "DRGT_RISKR", "HRCN_RISKR", "TRND_RISKR"]:
            if is_high(hazard_data.get(key, "")):
                high_count += 1
    if high_flood and high_count >= 1:
        return "High"
    elif high_flood or high_count >= 1:
        return "Medium"
    else:
        return "Low"

def generate_report(address_data, flood_data, hazard_data, agent_name, agent_contact, output_filename):
    overall = overall_risk_level(flood_data["zone"], hazard_data)
    flood_text = explain_flood_zone(flood_data["zone"])
    hazard_text = build_hazard_text(hazard_data)

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Property Climate Risk Report", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Prepared by: {agent_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Contact: {agent_contact}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Property Address", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 8, address_data["matched_address"])
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Overall Risk Level: {overall}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Flood Risk", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 8, flood_text)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Other Hazard Risks (County-Level, FEMA National Risk Index)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 8, hazard_text)
    pdf.ln(5)

    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 6, "Disclaimer: This report is for informational purposes only and is not a substitute for a professional inspection, insurance consultation, or official flood determination. Flood data sourced from FEMA NFHL. Other hazard data sourced from FEMA's National Risk Index at the county level.")

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
        generate_report(result, flood, hazard, agent_name, agent_contact, "risk_report.pdf")
    else:
        print("Could not find that address.")