#!/usr/bin/env python
# coding: utf-8

# KAYAK project UI : phase 7 - Streamlit dashboard
# Run with : streamlit run src/kayak_ui.py

import math
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATA_DIR_CSV  = Path("data/csv")
DATABASE_URL  = os.environ.get("DATABASE_URL")
TOP_N_HOTELS  = int(os.environ.get("TOP_N_HOTELS", 20))
HISTORY_DAYS  = int(os.environ.get("HISTORY_DAYS", 30))

st.set_page_config(page_title="KAYAK - Meilleures destinations en France", layout="wide")
st.title("KAYAK — Top destinations météo en France")


@st.cache_data
def get_forecast_period() -> tuple[str, str] | None:
    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL)
            r = pd.read_sql("""
                SELECT MIN(date_forecast) AS d_min, MAX(date_forecast) AS d_max
                FROM (
                    SELECT DISTINCT date_forecast FROM weather_scores_daily
                    ORDER BY date_forecast DESC LIMIT 4
                ) t
            """, engine)
            if not r.empty and r["d_min"].iloc[0]:
                fmt = lambda d: pd.to_datetime(d).strftime("%-d %B %Y")
                return fmt(r["d_min"].iloc[0]), fmt(r["d_max"].iloc[0])
        except Exception:
            pass
    return None


@st.cache_data
def get_extraction_date() -> str | None:
    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL)
            result = pd.read_sql("SELECT MAX(load_date) AS d FROM hotels", engine)
            if not result.empty and result["d"].iloc[0]:
                return pd.to_datetime(result["d"].iloc[0]).strftime("%-d %B %Y")
        except Exception:
            pass
    files = sorted(DATA_DIR_CSV.glob("*/weather-scores-[0-9]*.csv"))
    if files:
        m = re.search(r"(\d{8})", files[-1].name)
        if m:
            return datetime.strptime(m.group(1), "%Y%m%d").strftime("%-d %B %Y")
    return None


_extraction_date = get_extraction_date()
_forecast_period = get_forecast_period()
if _forecast_period:
    st.caption(f"Prévisions météo du {_forecast_period[0]} au {_forecast_period[1]}"
               + (f" — données extraites le {_extraction_date}" if _extraction_date else ""))
else:
    st.caption("Date d'extraction inconnue — vérifiez le pipeline.")


@st.cache_data
def load_weather_scores() -> pd.DataFrame:
    if DATABASE_URL:
        engine = create_engine(DATABASE_URL)
        return pd.read_sql("SELECT * FROM weather_scores ORDER BY score_final DESC", engine)
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


@st.cache_data(ttl=3600)
def load_score_history(city_id: str) -> pd.DataFrame:
    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL)
            return pd.read_sql("""
                SELECT date_forecast, score_day FROM weather_scores_daily
                WHERE city_id = %(city_id)s
                  AND date_forecast >= CURRENT_DATE - INTERVAL '1 day' * %(history_days)s
                ORDER BY date_forecast
            """, engine, params={"city_id": city_id, "history_days": HISTORY_DAYS})
        except Exception:
            pass
    return pd.DataFrame()


@st.cache_data
def load_hotels(city: str) -> pd.DataFrame | None:
    """Retourne None si DATABASE_URL absent ou erreur de connexion, DataFrame (éventuellement vide) sinon."""
    if not DATABASE_URL:
        return None
    try:
        engine = create_engine(DATABASE_URL)
        return pd.read_sql(
            f"SELECT * FROM hotels WHERE city_name = %(city)s ORDER BY load_date DESC, score DESC LIMIT {TOP_N_HOTELS}",
            engine, params={"city": city},
        )
    except Exception:
        return None


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
        hover_data={"score_final": ":.1f", "mean": ":.1f", "lat": False, "lon": False},
        size="score_final",
        color="score_final",
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
    df_rank = df_scores[["city_name", "score_final"]].copy()
    df_rank = df_rank.rename(columns={"score_final": "Score"})
    df_rank["city_name"] = [
        f"⭐ {c}" if i < 5 else c for i, c in enumerate(df_rank["city_name"])
    ]
    st.dataframe(
        df_rank.style.background_gradient(subset=["Score"], cmap="RdYlGn"),
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

if df_hotels is None:
    st.error("Erreur de connexion à la base de données — impossible de charger les hôtels.")
elif df_hotels.empty:
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
        col_map2, col_hotels = st.columns([2, 1])

        # Centrer sur le meilleur hôtel
        best = df_h.loc[df_h["score"].idxmax()]
        lat_min, lat_max = df_h["lat"].min(), df_h["lat"].max()
        lon_min, lon_max = df_h["lon"].min(), df_h["lon"].max()
        lat_span = max(lat_max - lat_min, 0.001)
        lon_span = max(lon_max - lon_min, 0.001)
        hotel_table_height = 35 * TOP_N_HOTELS + 38
        map_height = max(520, hotel_table_height)
        # Zoom pour englober tous les hôtels :
        # Formule Mapbox : zoom = log2(viewport_px / 256 × 360° / span°)
        #   - 256 = taille d'une tuile de référence en pixels
        #   - 360° / 180° = étendue totale lon / lat à zoom 0
        # On prend le min(zoom_lon, zoom_lat) pour garantir que les deux axes
        # sont visibles, puis -1 pour ajouter une marge de padding.
        zoom = max(1, min(round(min(
            math.log2(900 / 256 * 360 / lon_span),
            math.log2(map_height / 256 * 180 / lat_span),
        )) - 1, 15))

        with col_map2:
            fig2 = px.scatter_mapbox(
                df_h,
                lat="lat", lon="lon",
                hover_name="hotel_name",
                hover_data={"score": True, "address": True, "lat": False, "lon": False},
                size="score",
                color="score",
                color_continuous_scale="Blues",
                zoom=zoom,
                center={"lat": best["lat"], "lon": best["lon"]},
                height=map_height,
                mapbox_style="open-street-map",
                custom_data=["hotel_name", "score", "description", "url", "address"],
            )
            fig2.update_traces(marker=dict(opacity=0.9, sizemin=8))
            fig2.update_layout(coloraxis_colorbar=dict(title="Score<br>Booking"), margin=dict(r=0))

            event2 = st.plotly_chart(fig2, use_container_width=True, on_select="rerun", key="map2")

        with col_hotels:
            st.markdown(f"**Tableau 2 — Top {TOP_N_HOTELS} hôtels**")
            # Colonne "Hôtel" = url#hotel_name — LinkColumn extrait le nom affiché via regex #(.+)$
            df_tab2 = df_h.sort_values("score", ascending=False).head(TOP_N_HOTELS).copy()
            df_tab2["Hôtel"] = df_tab2["url"].fillna("") + "#" + df_tab2["hotel_name"].fillna("")
            st.dataframe(
                df_tab2[["Hôtel", "score", "address"]],
                use_container_width=True,
                height=hotel_table_height,
                hide_index=True,
                column_config={
                    "Hôtel": st.column_config.LinkColumn("Hôtel", display_text=r"#(.+)$"),
                    "score": st.column_config.NumberColumn("Score"),
                    "address": st.column_config.TextColumn("Adresse"),
                },
            )

        # Détail hôtel sur clic — affiché sous les deux colonnes
        if event2 and event2.selection and event2.selection.points:
            pt = event2.selection.points[0]
            cd = pt.get("customdata", [])
            if len(cd) >= 4:
                h_name, h_score, h_desc, h_url = cd[0], cd[1], cd[2], cd[3]
                h_addr = cd[4] if len(cd) >= 5 else None
                with st.container(border=True):
                    st.markdown(f"### {h_name}")
                    st.markdown(f"**Score Booking :** {h_score}")
                    if h_addr:
                        st.markdown(f"**Adresse :** {h_addr}")
                    st.markdown(h_desc or "_Pas de description disponible._")
                    if h_url:
                        st.markdown(f"[Voir sur Booking.com]({h_url})")

# BLOC 3 : historique scores météo 30 jours

st.divider()
st.subheader(f"Historique scores météo — {selected_city} ({HISTORY_DAYS} derniers jours)")

city_id_sel = df_scores.loc[df_scores["city_name"] == selected_city, "city_id"].iloc[0] \
    if not df_scores[df_scores["city_name"] == selected_city].empty else selected_city

df_hist = load_score_history(city_id_sel)

if df_hist.empty:
    st.info("Aucun historique disponible — les données s'accumuleront au fil des extractions quotidiennes.")
else:
    df_hist["date_forecast"] = pd.to_datetime(df_hist["date_forecast"])
    fig3 = px.line(
        df_hist,
        x="date_forecast",
        y="score_day",
        markers=True,
        labels={"date_forecast": "Date", "score_day": "Score météo"},
        color_discrete_sequence=["#2196F3"],
    )
    fig3.update_traces(line=dict(width=2), marker=dict(size=6))
    fig3.update_layout(
        yaxis=dict(range=[0, 100], title="Score météo (/100)"),
        xaxis_title=None,
        margin=dict(t=20, b=20),
        height=300,
    )
    fig3.add_hrect(y0=80, y1=100, fillcolor="green",  opacity=0.07, line_width=0)
    fig3.add_hrect(y0=60, y1=80,  fillcolor="yellow", opacity=0.07, line_width=0)
    fig3.add_hrect(y0=40, y1=60,  fillcolor="orange", opacity=0.07, line_width=0)
    fig3.add_hrect(y0=0,  y1=40,  fillcolor="red",    opacity=0.07, line_width=0)
    st.plotly_chart(fig3, use_container_width=True)
