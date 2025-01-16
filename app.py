import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import streamlit as st
import country_converter as coco
import matplotlib.pyplot as plt

cc = coco.CountryConverter()

# Load data
geojson_file = "geojson/world.geojson"
brassica_file = "data/brassica.csv"
climate_file = "data/merged_data.csv"

# Read GeoJSON and CSV data
geo_data = gpd.read_file(geojson_file)
brassica_data = pd.read_csv(brassica_file)
climate_data = pd.read_csv(climate_file, delimiter=";")

# Streamlit app
st.title("Plant Survival Visualization")

# Dropdown for plant species
brassica_data["plant_variety"] = (
    brassica_data["species"] + " - " + brassica_data["variety"]
)
plants_names_ordered = sorted(brassica_data["plant_variety"])
selected_plant = st.selectbox("Select a Plant Species", plants_names_ordered)

# Slider for year
start_year = climate_data["year"].min()
end_year = climate_data["year"].max()
year = st.slider("Select a Year", start_year, end_year, 2025, step=1)


# Extract selected plant data
selected_plant_data = brassica_data[
    brassica_data["plant_variety"] == selected_plant
].iloc[0]
min_temp = selected_plant_data["min_temp"]
max_temp = selected_plant_data["max_temp"]
min_prec = selected_plant_data["min_prec"]
max_prec = selected_plant_data["max_prec"]


# Filter climate data for the selected year
climate_year_data = climate_data[climate_data["year"] == year]
climate_year_data.loc[:, "country"] = cc.convert(
    climate_year_data["country"], to="name_short"
)


# Map creation
map_center = [20, 0]  # Adjust as needed
m = folium.Map(location=map_center, zoom_start=2)


st.subheader("Adjust Survivability Score Weights")
col1, col2 = st.columns(2)
with col1:
    weight_slider = st.slider("Temperature Weight (%)", 0, 100, 50, 1)
with col2:
    st.write(f"Temperature Weight: **{weight_slider}%**")
    st.write(f"Precipitation Weight: **{100 - weight_slider}%**")
temp_weight = weight_slider / 100
prec_weight = 1 - temp_weight

st.subheader("Map Visualization")


# Function to calculate survivability score
def calculate_survivability(row, min_temp, max_temp, min_prec, max_prec):
    # Temperature overlap score (0 to 1)
    temp_overlap = max(
        0, min(max_temp, row["max_temp"]) - max(min_temp, row["min_temp"])
    ) / (max_temp - min_temp)

    # Precipitation overlap score (0 to 1)
    prec_overlap = max(
        0, min(max_prec, row["max_prec"]) - max(min_prec, row["min_prec"])
    ) / (max_prec - min_prec)

    # Survivability score (weighted average)
    return temp_overlap * temp_weight + prec_overlap * prec_weight  # Equal weighting


# Function to map score to color
def survivability_to_color(score):
    # Use a colormap from matplotlib (e.g., 'viridis' or 'RdYlGn')
    colormap = plt.cm.RdYlGn  # Red to green spectrum
    rgba = colormap(score)  # Map score (0 to 1) to RGBA
    return f"rgba({int(rgba[0] * 255)}, {int(rgba[1] * 255)}, {int(rgba[2] * 255)}, {rgba[3]})"


# Updated style function
def style_function(feature):
    country_name = feature["properties"]["name"]
    country_name = cc.convert(names=country_name, to="name_short")
    country_climate = climate_year_data[climate_year_data["country"] == country_name]

    if not country_climate.empty:
        survivability_score = calculate_survivability(
            country_climate.iloc[0], min_temp, max_temp, min_prec, max_prec
        )
        color = survivability_to_color(survivability_score)
        return {
            "fillColor": color,
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.7,
        }
    else:
        return {
            "fillColor": "gray",
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.7,
        }


# Prepare tooltip information
tooltip_info = {}
for _, feature in geo_data.iterrows():
    country_name = feature["name"]
    country_name = cc.convert(names=country_name, to="name_short")
    match = climate_year_data[climate_year_data["country"] == country_name]
    if not match.empty:
        tooltip_info[feature.name] = {
            "min_temp": match.iloc[0]["min_temp"],
            "max_temp": match.iloc[0]["max_temp"],
            "min_prec": match.iloc[0]["min_prec"],
            "max_prec": match.iloc[0]["max_prec"],
        }

geo_data["min_temp"] = geo_data.index.map(
    lambda idx: tooltip_info.get(idx, {}).get("min_temp", "N/A")
)
geo_data["max_temp"] = geo_data.index.map(
    lambda idx: tooltip_info.get(idx, {}).get("max_temp", "N/A")
)
geo_data["min_prec"] = geo_data.index.map(
    lambda idx: tooltip_info.get(idx, {}).get("min_prec", "N/A")
)
geo_data["max_prec"] = geo_data.index.map(
    lambda idx: tooltip_info.get(idx, {}).get("max_prec", "N/A")
)

# Add GeoJSON layer to the map
folium.GeoJson(
    geo_data,
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(
        fields=["name", "min_temp", "max_temp", "min_prec", "max_prec"],
        aliases=["Country:", "Min Temp:", "Max Temp:", "Min Prec:", "Max Prec:"],
    ),
).add_to(m)


# Render map
st_folium(m, width=700, height=500)


# Display selected plant information
st.subheader("Selected Plant Information")
st.write(f"**Species:** {selected_plant_data['species']}")
st.write(f"**Variety:** {selected_plant_data['variety']}")
st.write(f"**Protein Content:** {selected_plant_data['protein']} g")
st.write(f"**Temperature Tolerance:** {min_temp}°C to {max_temp}°C")
st.write(f"**Precipitation Tolerance:** {min_prec} mm to {max_prec} mm")
