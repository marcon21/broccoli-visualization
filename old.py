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
geojson_files = list(os.listdir(Countrygeojson_dir))

# Select a file
selected_file = st.selectbox("Select a GeoJSON file", geojson_files, index=0)
gdf = gpd.read_file(os.path.join(geojson_dir, selected_file))
name_field = "NAME" if "NAME" in gdf.columns else "name"


# Year slider
start_year = 2000
end_year = 2050
step = 5
year_slider = st.slider("Year", start_year, end_year, 2020, step)

# Generate map
map_center = [50, 10]
m = folium.Map(location=map_center, zoom_start=3)

# Create fake dataset
fake_dataset = {}

for i in range(start_year, end_year + 1, step):
    for _, row in gdf.iterrows():
        fake_dataset[f"{row[name_field]}_{i}"] = {
            # "value": random.randint(0, 200),
            "value": (row.geometry.centroid.x + i * 2)
            % 200,
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
        aliases=[":"],
        localize=True,
    ),
    style_function=lambda x: {
        "fillColor": colormap(
            fake_dataset[f'{x["properties"][name_field]}_{year_slider}']["value"]
        ),
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

    # print(len(marker_cluster._children))s


add_random_markers(m, gdf, gdf.total_bounds, num_markers=100)


# Render map in Streamlit
st_folium(m, width=700, height=500)
