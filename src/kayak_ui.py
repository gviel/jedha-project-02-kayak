#!/usr/bin/env python
# coding: utf-8

# KAYAK project UI : phase 7 - Streamlit dashboard
# Run with : streamlit run src/kayak_ui.py

import math
import os
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATA_DIR_CSV = Path("data/csv")
DATABASE_URL = os.environ.get("DATABASE_URL")

st.set_page_config(page_title="KAYAK - Meilleures destinations en France", layout="wide")
st.title("KAYAK — Top destinations météo en France")


@st.cache_data
def load_weather_scores() -> pd.DataFrame:
    if DATABASE_URL:
        engine = create_engine(DATABASE_URL)
        return pd.read_sql("SELECT * FROM weather_scores ORDER BY mean DESC", engine)
    files = sorted(DATA_DIR_CSV.glob("*/weather-scores-[0-9]*.csv"))
    if not files:
        return pd.DataFrame()
    return pd.read_csv(files[-1])


@st.cache_data
def load_cities() -> pd.DataFrame:
    if DATABASE_URL:
        engine = create_engine(DATABASE_URL)
        return pd.read_sql("SELECT * FROM cities", engine)
    p = DATA_DIR_CSV / "cities.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


@st.cache_data
def load_hotels(city: str) -> pd.DataFrame:
    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL)
            df = pd.read_sql(
                "SELECT * FROM hotels WHERE city_name = %(city)s ORDER BY load_date DESC, score DESC LIMIT 20",
                engine, params={"city": city},
            )
            if not df.empty:
                return df
        except Exception:
            pass
    # fallback CSV local
    city_id = city.replace(" ", "_").replace("'", "_")
    # files = sorted(DATA_DIR_CSV.glob(f"[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]/hotels-{city_id}-*.csv"))
    # glob */*.csv puis filtre les répertoires dont le nom est exactement 8 chiffres
    files = [f for f in sorted(DATA_DIR_CSV.glob(f"*/hotels-{city_id}-*.csv")) if re.match(r"\d{8}$", f.parent.name)]
    if not files:
        return pd.DataFrame()
    return pd.read_csv(files[-1])


# Chargement données

df_scores = load_weather_scores()
df_cities = load_cities()

if df_scores.empty:
    st.warning("Aucune donnée de scoring disponible — lancez d'abord le pipeline.")
    st.stop()

df = df_scores.merge(df_cities, on="city_name", how="left")

# Session state

if "selected_city" not in st.session_state:
    st.session_state.selected_city = df["city_name"].iloc[0]

# BLOC 1 : carte météo + classement côte à côte

st.subheader(f"Destinations météo — scores sur 4 jours ({len(df_scores)} villes)")

col_map1, col_rank = st.columns([3, 1])

df_map = df.dropna(subset=["lat", "lon"]).copy()

with col_map1:
    fig1 = px.scatter_mapbox(
        df_map,
        lat="lat", lon="lon",
        hover_name="city_name",
        hover_data={"mean": ":.1f", "lat": False, "lon": False},
        size="mean",
        color="mean",
        color_continuous_scale="RdYlGn",
        zoom=4,
        height=520,
        mapbox_style="carto-positron",
        custom_data=["city_name"],
    )
    fig1.update_traces(marker=dict(opacity=0.8, sizemin=6))
    fig1.update_layout(coloraxis_colorbar=dict(title="Score<br>météo"), margin=dict(r=0))

    # Étiquettes pour le top 5
    top5 = df_map.head(5)
    fig1.add_trace(go.Scattermapbox(
        lat=top5["lat"],
        lon=top5["lon"],
        mode="text",
        text=top5["city_name"],
        textfont=dict(size=11, color="black"),
        hoverinfo="skip",
        showlegend=False,
    ))

    event1 = st.plotly_chart(fig1, use_container_width=True, on_select="rerun", key="map1")

    # Mise à jour ville sélectionnée via clic carte 1
    if event1 and event1.selection and event1.selection.points:
        clicked = event1.selection.points[0].get("customdata", [None])[0]
        if clicked:
            st.session_state.selected_city = clicked

with col_rank:
    st.markdown("**Classement des villes**")
    df_rank = df_scores[["city_name", "mean"]].copy()
    df_rank["city_name"] = [
        f"⭐ {c}" if i < 5 else c for i, c in enumerate(df_rank["city_name"])
    ]
    st.dataframe(
        df_rank.style.background_gradient(subset=["mean"], cmap="RdYlGn"),
        use_container_width=True,
        height=510,
        hide_index=True,
    )

# Selectbox synchronisé avec le clic — en dessous du bloc carte/classement
cities_list = df["city_name"].tolist()
max_city_len = max(len(c) for c in cities_list)
col_sel, _ = st.columns([max_city_len, 80 - max_city_len])
with col_sel:
    selected_city = st.selectbox(
        "Sélectionner une ville pour voir ses hôtels :",
        cities_list,
        index=cities_list.index(st.session_state.selected_city)
              if st.session_state.selected_city in cities_list else 0,
        key="city_select",
    )
st.session_state.selected_city = selected_city

# BLOC 2 : hôtels

st.divider()
st.subheader(f"Hôtels à {selected_city}")

df_hotels = load_hotels(selected_city)

if df_hotels.empty:
    st.info(
        f"Aucun hôtel disponible pour **{selected_city}** "
        "— lancez d'abord `scraper_hotels.py`."
    )
else:
    df_h = df_hotels.copy()
    df_h["lat"]   = pd.to_numeric(df_h["lat"],   errors="coerce")
    df_h["lon"]   = pd.to_numeric(df_h["lon"],   errors="coerce")
    df_h["score"] = pd.to_numeric(df_h["score"], errors="coerce")
    df_h = df_h.dropna(subset=["lat", "lon", "score"])

    if df_h.empty:
        st.info("Coordonnées géographiques manquantes pour les hôtels de cette ville.")
    else:
        col_map2, col_hotels = st.columns([3, 1])

        # Centrer sur le meilleur hôtel
        best = df_h.loc[df_h["score"].idxmax()]
        lat_min, lat_max = df_h["lat"].min(), df_h["lat"].max()
        lon_min, lon_max = df_h["lon"].min(), df_h["lon"].max()
        lat_span = max(lat_max - lat_min, 0.001)
        lon_span = max(lon_max - lon_min, 0.001)
        # Zoom pour englober tous les hôtels :
        # Formule Mapbox : zoom = log2(viewport_px / 256 × 360° / span°)
        #   - 256 = taille d'une tuile de référence en pixels
        #   - 900 / 520 = dimensions approx. du conteneur carte (px)
        #   - 360° / 180° = étendue totale lon / lat à zoom 0
        # On prend le min(zoom_lon, zoom_lat) pour garantir que les deux axes
        # sont visibles, puis -1 pour ajouter une marge de padding.
        zoom = max(1, min(round(min(
            math.log2(900 / 256 * 360 / lon_span),
            math.log2(520 / 256 * 180 / lat_span),
        )) - 1, 15))

        with col_map2:
            fig2 = px.scatter_mapbox(
                df_h,
                lat="lat", lon="lon",
                hover_name="hotel_name",
                hover_data={"score": True, "lat": False, "lon": False},
                size="score",
                color="score",
                color_continuous_scale="Blues",
                zoom=zoom,
                center={"lat": best["lat"], "lon": best["lon"]},
                height=520,
                mapbox_style="open-street-map",
                custom_data=["hotel_name", "score", "description", "url"],
            )
            fig2.update_traces(marker=dict(opacity=0.9, sizemin=8))
            fig2.update_layout(coloraxis_colorbar=dict(title="Score<br>Booking"), margin=dict(r=0))

            event2 = st.plotly_chart(fig2, use_container_width=True, on_select="rerun", key="map2")

        with col_hotels:
            st.markdown("**Top 20 hôtels**")
            st.dataframe(
                df_h[["hotel_name", "score", "url"]].sort_values("score", ascending=False),
                use_container_width=True,
                height=510,
                hide_index=True,
                column_config={"url": st.column_config.LinkColumn("Lien Booking")},
            )

        # Détail hôtel sur clic — affiché sous les deux colonnes
        if event2 and event2.selection and event2.selection.points:
            pt = event2.selection.points[0]
            cd = pt.get("customdata", [])
            if len(cd) >= 4:
                h_name, h_score, h_desc, h_url = cd[0], cd[1], cd[2], cd[3]
                with st.container(border=True):
                    st.markdown(f"### {h_name}")
                    st.markdown(f"**Score Booking :** {h_score}")
                    st.markdown(h_desc or "_Pas de description disponible._")
                    if h_url:
                        st.markdown(f"[Voir sur Booking.com]({h_url})")
