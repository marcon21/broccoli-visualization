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

st.title("Plant Survival Visualization")

with st.expander("About the project", expanded=False):
    st.markdown(
        """<div style="text-align: justify;">
    The sustainable production of food is a critical challenge due to global climate change, increasing the importance of innovative approaches to agriculture. This study explores the Brassicaceae family as a potential source of climate-resilient, protein-rich crops. We compile a structured dataset of 134 Brassicaceae species, including information on protein content, temperature, precipitation tolerance, and countries in which they currently grow. Using climate projections from the CMIP6-x0.25 model, we develop a survivability function to predict the chance of survival of these species from 2025 to 2100. The final output is an interactive web-based visualization tool, that enables users to identify countries best suited for growing Brassicaceae crops based on future climate conditions.    
    </div></br>""",
        unsafe_allow_html=True,
    )

brassica_data["plant_variety"] = (
    brassica_data["species"] + " - " + brassica_data["variety"]
)
plants_names_ordered = sorted(brassica_data["plant_variety"])
selected_plant = st.selectbox("Select a Plant Species", plants_names_ordered)

start_year = climate_data["year"].min()
end_year = climate_data["year"].max()
year = st.slider("Select a Year", start_year, end_year, 2025, step=1)


selected_plant_data = brassica_data[
    brassica_data["plant_variety"] == selected_plant
].iloc[0]
min_temp = selected_plant_data["min_temp"]
max_temp = selected_plant_data["max_temp"]
min_prec = selected_plant_data["min_prec"]
max_prec = selected_plant_data["max_prec"]


climate_year_data = climate_data[climate_data["year"] == year]
climate_year_data.loc[:, "country"] = cc.convert(
    climate_year_data["country"], to="name_short"
)


map_center = [20, 0]
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


def calculate_survivability(
    row,
    min_temp,
    max_temp,
    min_prec,
    max_prec,
):
    def calculate_overlap_score(min_plant, max_plant, min_climate, max_climate):
        plant_range = max_plant - min_plant  # Calculate plant range

        if min_climate >= min_plant and max_climate <= max_plant:  # Perfect overlap
            return 1.0
        elif max_climate < min_plant or min_climate > max_plant:  # No overlap
            return 0.0
        else:  # Partial overlap
            overlap_start = max(min_plant, min_climate)
            overlap_end = min(max_plant, max_climate)
            overlap_range = overlap_end - overlap_start
            return max(0, overlap_range / plant_range)  # Normalize by plant range

    temp_score = calculate_overlap_score(
        min_temp, max_temp, row["min_temp"], row["max_temp"]
    )

    prec_score = calculate_overlap_score(
        min_prec, max_prec, row["min_prec"], row["max_prec"]
    )

    survivability_score = (temp_weight * temp_score) + (prec_weight * prec_score)

    return round(survivability_score, 3)


colormap = linear.RdYlGn_11.scale(
    0,
    1,
)

colormap.caption = "Survivability Score"
colormap.add_to(m)


def compute_all_survivability(
    min_temp=min_temp,
    max_temp=max_temp,
    min_prec=min_prec,
    max_prec=max_prec,
    climate_year_data=climate_year_data,
):
    score_values = {}
    for idx, row in climate_year_data.iterrows():
        country_name = row["country"]
        country_name = cc.convert(names=country_name, to="name_short")
        country_climate = climate_year_data[
            climate_year_data["country"] == country_name
        ]
        survivability_score = calculate_survivability(
            country_climate.iloc[0], min_temp, max_temp, min_prec, max_prec
        )

        score_values[country_name] = survivability_score

    return score_values


score_values = compute_all_survivability()


def style_function(feature):
    global score_values
    country_name = feature["properties"]["name"]
    country_name = cc.convert(names=country_name, to="name_short")
    country_climate = climate_year_data[climate_year_data["country"] == country_name]

    if not country_climate.empty:
        survivability_score = score_values[country_name]
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
geo_data["surv_score"] = geo_data.name.map(
    lambda x: score_values.get(cc.convert(names=x, to="name_short"), "N/A")
)

folium.GeoJson(
    geo_data,
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(
        fields=[
            "name",
            "min_temp",
            "max_temp",
            "min_prec",
            "max_prec",
            "surv_score",
        ],
        aliases=[
            "Country:",
            "Min Temp:",
            "Max Temp:",
            "Min Prec:",
            "Max Prec:",
            "Survivability Score:",
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

    if area:
        for a in sorted(area.toJSON(), key=lambda x: x["importance"], reverse=True):
            latitude = a["lat"]
            longitude = a["lon"]
            yield latitude, longitude

    yield None


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
