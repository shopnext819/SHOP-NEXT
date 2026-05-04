import json
import os

file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "New Text Document.txt")

data = {
    "pakistan_map": {}, 
    "countries": []
}

with open(file_path, "r", encoding="utf-8") as f:
    lines = [L.strip() for L in f.readlines() if L.strip()]
    
parsing_countries = False

for line in lines:
    if line.lower() == "countries:":
        parsing_countries = True
        continue
    
    if not parsing_countries:
        if "—" in line:  # Check for em-dash
            parts = line.split("—")
        elif "-" in line:
            parts = line.split("-")
        else:
            continue
            
        if len(parts) == 2:
            city = parts[0].strip()
            province = parts[1].strip()
            
            if province not in data["pakistan_map"]:
                data["pakistan_map"][province] = []
            
            data["pakistan_map"][province].append(city)
            
    else:
        # Parsing Countries
        if line.startswith("-"):
            country = line[1:].strip()
            data["countries"].append(country)
        elif line.lower() not in ["all country", "countries:"] and line:
            # specifically for the last few palestine, kashmir, mayamar [barma]
            data["countries"].append(line.strip())

# Sort cities inside provinces alphabetically!
for p in data["pakistan_map"]:
    data["pakistan_map"][p] = sorted(list(set(data["pakistan_map"][p])))

# Ensure Pakistan is removed from the "Other" countries list since we handle it natively!
if "Pakistan" in data["countries"]:
    data["countries"].remove("Pakistan")
    
data["countries"] = sorted(list(set(data["countries"])))

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "location_data_js.txt")
with open(output_path, "w", encoding="utf-8") as f:
    f.write("const LOCATION_DATA = " + json.dumps(data, indent=4) + ";")
    
print("Parsing complete! Output in location_data_js.txt")
