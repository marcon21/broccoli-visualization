import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import streamlit as st
import country_converter as coco
import matplotlib.pyplot as plt
from branca.colormap import linear
from folium.plugins import MarkerCluster
from OSMPythonTools.overpass import Overpass
from OSMPythonTools.nominatim import Nominatim
import random


overpass = Overpass()
nominatim = Nominatim()

cc = coco.CountryConverter()

# Load data
geojson_file = "geojson/world.geojson"
brassica_file = "data/brassica.csv"
climate_file = "data/merged_data.csv"

# Read GeoJSON and CSV data
geo_data = gpd.read_file(geojson_file)
brassica_data = pd.read_csv(brassica_file)
climate_data = pd.read_csv(climate_file)

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


tooltip_info = {}


st.subheader("Adjust Survivability Score Weights")
with st.expander("Different weights?", expanded=False):
    st.write(
        """
        The weights determine the relative importance of temperature and precipitation 
        when calculating the survivability score. 
        - **Temperature Weight (%)**:  Higher values emphasize the impact of temperature, leading to more significant changes in country distribution based on temperature suitability.
        - **Precipitation Weight (%)**: Higher values prioritize plant attributes being within the required range of precipitation for normal growth. This may result in subtle differences in distribution.

        """
    )
col1, col2 = st.columns(2)
with col1:
    weight_slider = st.slider("Weights (%)", 0, 100, 50, 1)
with col2:
    st.write(f"Temperature: **{weight_slider}%**")
    st.write(f"Precipitation: **{100 - weight_slider}%**")
temp_weight = weight_slider / 100
prec_weight = 1 - temp_weight

st.subheader("Map Visualization")


def calculate_survivability(row, min_temp, max_temp, min_prec, max_prec):
    # Temperature survivability
    if row["max_temp"] < min_temp or row["min_temp"] > max_temp:
        temp_score = 0  # No overlap
    elif min_temp <= row["min_temp"] and row["max_temp"] <= max_temp:
        temp_score = 1  # Perfect overlap
    else:
        # Partial overlap: calculate proportion of overlap
        overlap_start = max(min_temp, row["min_temp"])
        overlap_end = min(max_temp, row["max_temp"])
        overlap_range = overlap_end - overlap_start
        plant_range = max_temp - min_temp
        temp_score = max(0, overlap_range / plant_range)

    # Precipitation survivability
    if row["max_prec"] < min_prec or row["min_prec"] > max_prec:
        prec_score = 0  # No overlap
    elif min_prec <= row["min_prec"] and row["max_prec"] <= max_prec:
        prec_score = 1  # Perfect overlap
    else:
        # Partial overlap: calculate proportion of overlap
        overlap_start = max(min_prec, row["min_prec"])
        overlap_end = min(max_prec, row["max_prec"])
        overlap_range = overlap_end - overlap_start
        plant_range = max_prec - min_prec
        prec_score = max(0, overlap_range / plant_range)

    # Combine scores with weights
    survivability_score = temp_weight * temp_score + prec_weight * prec_score

    return round(survivability_score, 3)


colormap = linear.RdYlGn_11.scale(
    0,
    1,
)

colormap.caption = "COLORMAP TEST"
colormap.add_to(m)


# Updated style function
def style_function(feature):
    country_name = feature["properties"]["name"]
    country_name = cc.convert(names=country_name, to="name_short")
    country_climate = climate_year_data[climate_year_data["country"] == country_name]

    if not country_climate.empty:
        survivability_score = calculate_survivability(
            country_climate.iloc[0], min_temp, max_temp, min_prec, max_prec
        )
        color = colormap(survivability_score)
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
        aliases=[
            "Country:",
            "Min Temp:",
            "Max Temp:",
            "Min Prec:",
            "Max Prec:",
        ],
    ),
).add_to(m)

folium.plugins.Fullscreen(
    position="topright",
    title="Expand me",
    title_cancel="Exit me",
    force_separate_button=True,
).add_to(m)


def get_coordinates(place_name):
    area = nominatim.query(place_name)
    # from pprint import pprint

    if area:
        # pprint(sorted(area.toJSON(), key=lambda x: x["importance"], reverse=True))
        # print()
        for a in sorted(area.toJSON(), key=lambda x: x["importance"], reverse=True):
            latitude = a["lat"]
            longitude = a["lon"]
            yield latitude, longitude

    yield None


# Add random markers
def add_markers(map_obj):
    marker_cluster = MarkerCluster().add_to(map_obj)
    plant_countries = selected_plant_data["country"].split(",")

    random.seed(42)
    # st.write(plant_countries)
    for place in plant_countries:
        coordinates = next(get_coordinates(place.strip()), None)
        # for coordinates in get_coordinates(place.strip()):
        if coordinates:
            # st.write(f"Coordinates for {place}: {coordinates}")
            # Randomly offset the coordinates by a small amount
            offset_coordinates = [
                float(coordinates[0]) + random.uniform(-0.1, 0.1),
                float(coordinates[1]) + random.uniform(-0.1, 0.1),
            ]

            folium.Marker(
                location=offset_coordinates,
                popup=place,
                icon=folium.Icon(color="green", icon="leaf"),
            ).add_to(marker_cluster)


add_markers(m)

colormap.add_to(m)

# Render map
st_folium(m, width=700, height=500)


# Display selected plant information
st.subheader("Selected Plant Information")
with st.expander("Data extraction sources", expanded=False):
    st.write(
        """
        - **Brassicaceae Databases**: Scraped and processed using LLMs for keywords like protein content, plant variety, and temperature.
         - **Databases**: Information from the [USDA](https://www.usda.gov) and [PROTA4U Database](https://prota.prota4u.org).
        - **BeautifulSoup Library**: Used for web scraping and exporting data as JSON files.
        - **Camelot Library**: Extracted protein content tables from PDFs.
        - **Google Search**: Aggregated data for missing entries.

        **Final dataset**: 134 complete entries (Kappa Score of 67%).

        
        """
    )
st.write(f"**Species:** {selected_plant_data['species']}")
st.write(f"**Variety:** {selected_plant_data['variety']}")
st.write(f"**Protein Content:** {selected_plant_data['protein']} g")
st.write(f"**Temperature Tolerance:** {min_temp}°C to {max_temp}°C")
st.write(f"**Precipitation Tolerance:** {min_prec} mm to {max_prec} mm")


@st.cache_data
def convert_to_csv(df):
    """Converts a DataFrame to CSV format."""
    return df.to_csv(index=False).encode("utf-8")


# Option 1: Export Filtered Climate Data
filtered_csv = convert_to_csv(climate_year_data)
st.download_button(
    label="Download Climate Data",
    data=filtered_csv,
    file_name=f"climate_data_{year}.csv",
    mime="text/csv",
)
