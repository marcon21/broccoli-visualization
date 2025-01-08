import os
import random
import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from branca.colormap import linear

random.seed(42)

st.title("GeoJSONs with Streamlit and Folium")

# Load GeoJSON files
geojson_dir = "geojson"
geojson_files = list(os.listdir(geojson_dir))

# Select a file
selected_file = st.selectbox("Select a GeoJSON file", geojson_files, index=0)
gdf = gpd.read_file(os.path.join(geojson_dir, selected_file))

# Determine name field
name_field = "NAME" if "NAME" in gdf.columns else "name"

# Generate map
map_center = [50, 10]
m = folium.Map(location=map_center, zoom_start=3)

# Create fake dataset
fake_dataset = {
    row[name_field]: {
        "value": row.geometry.centroid.x,
        "lat": row.geometry.centroid.y,
        "lon": row.geometry.centroid.x,
    }
    for _, row in gdf.iterrows()
}

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
    # zoom_on_click=True,
    tooltip=folium.GeoJsonTooltip(
        fields=[name_field],
        aliases=["Country:"],
        localize=True,
    ),
    style_function=lambda x: {
        "fillColor": colormap(fake_dataset[x["properties"][name_field]]["value"]),
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


# Add random markers
def add_random_markers(map_obj, gdf, bounds, num_markers=100):
    marker_cluster = MarkerCluster().add_to(map_obj)
    for _ in range(num_markers):
        while True:
            lat = random.uniform(bounds[1], bounds[3])  # miny, maxy
            lon = random.uniform(bounds[0], bounds[2])  # minx, maxx
            point = gpd.GeoSeries([gpd.points_from_xy([lon], [lat])[0]])
            if gdf.contains(
                point.iloc[0]
            ).any():  # Check if the point is within any polygon
                folium.Marker(
                    location=[lat, lon],
                    popup=f"Random Plant at {lat:.2f}, {lon:.2f}",
                    icon=folium.Icon(color="green", icon="leaf"),
                ).add_to(marker_cluster)
                break  # Exit the loop once a valid point is found

    # print(len(marker_cluster._children))


add_random_markers(m, gdf, gdf.total_bounds, num_markers=100)


# Render map in Streamlit
st_folium(m, width=700, height=500)
