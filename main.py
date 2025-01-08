# import streamlit as st
# import geopandas as gpd
# import folium
# from streamlit_folium import st_folium
# from folium.plugins import MarkerCluster
# import pandas as pd
# import json
# import random
# from branca.colormap import linear
# import os

# random.seed(42)

# st.title("GeoJSONs with Streamlit and Folium")

# geojson_dir = "geojson"
# name_field = "NAME"

# all_geojsons = list(os.listdir(geojson_dir))

# file = st.selectbox("Select a GeoJSON file", all_geojsons, index=0)

# gdf = gpd.read_file(os.path.join(geojson_dir, file))

# if name_field not in gdf.columns:
#     name_field = "name"

# # Create the map
# m = folium.Map([50, 10], zoom_start=3)

# fake_dataset = {}

# for i, row in gdf.iterrows():
#     fake_dataset[row[name_field]] = {
#         "value": row.geometry.centroid.x,
#         "lat": row.geometry.centroid.y,
#         "lon": row.geometry.centroid.x,
#     }

# colormap = linear.YlGn_09.scale(
#     min(fake_dataset.values(), key=lambda x: x["value"])["value"],
#     max(fake_dataset.values(), key=lambda x: x["value"])["value"],
# )
# colormap.caption = "Fake dataset"
# colormap.add_to(m)

# folium.GeoJson(
#     gdf,
#     zoom_on_click=True,
#     tooltip=folium.GeoJsonTooltip(
#         fields=[name_field],
#         aliases=["Country:"],
#         localize=True,
#     ),
#     style_function=lambda x: {
#         "fillColor": colormap(fake_dataset[x["properties"][name_field]]["value"]),
#         "color": "black",
#         "weight": 1,
#         "dashArray": "5, 5",
#         "fillOpacity": 0.9,
#     },
#     highlight_function=lambda x: {
#         "weight": 2,
#         "fillOpacity": 1,
#         "dashArray": "",
#     },
# ).add_to(m)

# # Add 100 random markers
# marker_cluster = MarkerCluster().add_to(m)

# bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
# for _ in range(100):
#     lat = random.uniform(bounds[1], bounds[3])  # miny, maxy
#     lon = random.uniform(bounds[0], bounds[2])  # minx, maxx
#     folium.Marker(
#         location=[lat, lon],
#         popup=f"Random Marker at {lat:.2f}, {lon:.2f}",
#         icon=folium.Icon(color="blue", icon="info-sign"),
#     ).add_to(marker_cluster)

# st_folium(m, width=700, height=500)


import os
import random
import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from branca.colormap import linear

random.seed(42)


# --- Utility Functions ---
def load_geojson_files(directory):
    """Load all GeoJSON files from a directory."""
    return list(os.listdir(directory))


def load_geodata(file_path):
    """Load GeoDataFrame from a GeoJSON file."""
    return gpd.read_file(file_path)


def create_fake_dataset(gdf, name_field):
    """Generate a fake dataset with centroids."""
    return {
        row[name_field]: {
            "value": row.geometry.centroid.x,
            "lat": row.geometry.centroid.y,
            "lon": row.geometry.centroid.x,
        }
        for _, row in gdf.iterrows()
    }


def add_random_markers(map_obj, bounds, num_markers=100):
    """Add random markers to the map within the specified bounds."""
    marker_cluster = MarkerCluster().add_to(map_obj)
    for _ in range(num_markers):
        lat = random.uniform(bounds[1], bounds[3])  # miny, maxy
        lon = random.uniform(bounds[0], bounds[2])  # minx, maxx
        folium.Marker(
            location=[lat, lon],
            popup=f"Random Marker at {lat:.2f}, {lon:.2f}",
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(marker_cluster)


def style_function(feature, colormap, dataset, name_field):
    """Style function for GeoJSON features."""
    return {
        "fillColor": colormap(dataset[feature["properties"][name_field]]["value"]),
        "color": "black",
        "weight": 1,
        "dashArray": "5, 5",
        "fillOpacity": 0.9,
    }


def highlight_function(feature):
    """Highlight function for GeoJSON features."""
    return {
        "weight": 2,
        "fillOpacity": 1,
        "dashArray": "",
    }


# --- Main App ---
st.title("GeoJSONs with Streamlit and Folium")

# Load GeoJSON files
geojson_dir = "geojson"
geojson_files = load_geojson_files(geojson_dir)

# Select a file
selected_file = st.selectbox("Select a GeoJSON file", geojson_files, index=0)
gdf = load_geodata(os.path.join(geojson_dir, selected_file))

# Determine name field
name_field = "NAME" if "NAME" in gdf.columns else "name"

# Generate map
map_center = [50, 10]
m = folium.Map(location=map_center, zoom_start=3)

# Create fake dataset
fake_dataset = create_fake_dataset(gdf, name_field)

# Add colormap
colormap = linear.YlGn_09.scale(
    min(fake_dataset.values(), key=lambda x: x["value"])["value"],
    max(fake_dataset.values(), key=lambda x: x["value"])["value"],
)
colormap.caption = "Fake dataset"
colormap.add_to(m)

# Add GeoJSON to the map
folium.GeoJson(
    gdf,
    zoom_on_click=True,
    tooltip=folium.GeoJsonTooltip(
        fields=[name_field],
        aliases=["Country:"],
        localize=True,
    ),
    style_function=lambda x: style_function(x, colormap, fake_dataset, name_field),
    highlight_function=highlight_function,  # Pass function reference, not a call
).add_to(m)

# Add random markers
add_random_markers(m, gdf.total_bounds, num_markers=100)

# Render map in Streamlit
st_folium(m, width=700, height=500)
