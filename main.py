import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import pandas as pd
import json
import random
from branca.colormap import linear

random.seed(42)

# url = "https://raw.githubusercontent.com/python-visualization/folium-example-data/main/us_states.json"
url = "https://raw.githubusercontent.com/leakyMirror/map-of-europe/refs/heads/master/GeoJSON/europe.geojson"

gdf = gpd.read_file(url)

m = folium.Map([50, 10], zoom_start=3)

fake_dataset = {}

for i, row in gdf.iterrows():
    fake_dataset[row["NAME"]] = {
        "value": i,
        "lat": row.geometry.centroid.y,
        "lon": row.geometry.centroid.x,
    }

colormap = linear.YlGn_09.scale(0, len(fake_dataset))
colormap.caption = "Fake dataset"
colormap.add_to(m)

folium.GeoJson(
    gdf,
    zoom_on_click=True,
    tooltip=folium.GeoJsonTooltip(
        fields=["NAME"],
        aliases=["Country:"],
        localize=True,
    ),
    style_function=lambda x: {
        "fillColor": colormap(fake_dataset[x["properties"]["NAME"]]["value"]),
        "color": "black",
        "weight": 1,
        "dashArray": "5, 5",
        "fillOpacity": 0.9,
    },
    highlight_function=lambda x: {
        "weight": 2,
        "fillOpacity": 1,
        "dashArray": "",
    },
).add_to(m)

folium.LayerControl().add_to(m)


st_folium(m, width=700, height=500)
