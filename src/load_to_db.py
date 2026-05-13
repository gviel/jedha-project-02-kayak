#!/usr/bin/env python
# coding: utf-8

# KAYAK project phase 6 : load CSV files from S3 into PostgreSQL (AWS RDS or Neon DB)
# Reads from s3://<S3_BUCKET>/<S3_PREFIX><YYYYMMDD>/, inserts into tables via SQLAlchemy.

import io
import os
import re
import sys
from datetime import datetime

import boto3
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL          = os.environ["DATABASE_URL"]
S3_BUCKET             = os.environ["S3_BUCKET"]
S3_PREFIX             = os.environ.get("S3_PREFIX", "csv/")
AWS_ACCESS_KEY_ID     = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_REGION            = os.environ.get("AWS_REGION", "eu-west-3")

TODAY = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)
engine = create_engine(DATABASE_URL)


def read_s3_csv(key: str) -> pd.DataFrame:
    obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    return pd.read_csv(io.BytesIO(obj["Body"].read()))


def list_s3_keys(prefix: str) -> list[str]:
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


if __name__ == "__main__":
    date_prefix = f"{S3_PREFIX}{TODAY}/"
    all_keys = list_s3_keys(date_prefix)

    # --- weather_scores_daily ---
    # Données recalculées chaque jour : remplacement complet de la table.
    daily_keys = [k for k in all_keys if re.search(r"weather-scores-daily-\d{8}\.csv$", k)]
    if daily_keys:
        df = read_s3_csv(daily_keys[-1])
        df.to_sql("weather_scores_daily", engine, if_exists="replace", index=False)
        print(f"[OK] weather_scores_daily — {len(df)} rows")
    else:
        print("[SKIP] no weather_scores_daily file found in S3")

    # --- weather_scores (summary) ---
    # Agrégat 4 jours recalculé chaque jour : remplacement complet de la table.
    summary_keys = [k for k in all_keys if re.search(r"weather-scores-\d{8}\.csv$", k)]
    if summary_keys:
        df = read_s3_csv(summary_keys[-1])
        df.to_sql("weather_scores", engine, if_exists="replace", index=False)
        print(f"[OK] weather_scores — {len(df)} rows")
    else:
        print("[SKIP] no weather_scores summary file found in S3")

    # --- hotels ---
    # Stratégie upsert : une seule ligne par hôtel (clé = city_id + hotel_name).
    # À chaque chargement :
    hotel_keys = [k for k in all_keys if re.search(r"hotels-.*-\d{8}\.csv$", k)]
    if hotel_keys:
        #   1. Lire les nouveaux fichiers S3 (load_date extraite du nom de fichier)
        frames = []
        for k in hotel_keys:
            df = read_s3_csv(k)
            m = re.search(r"-(\d{8})\.csv$", k)
            df["load_date"] = m.group(1) if m else TODAY
            frames.append(df)
        df_new = pd.concat(frames, ignore_index=True)

        #   2. Fusionner avec les données existantes en base
        try:
            df_existing = pd.read_sql("SELECT * FROM hotels", engine)
        except Exception:
            df_existing = pd.DataFrame()
        
        #   3. Dédupliquer en gardant la ligne avec la load_date la plus récente
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
        df_all = (
            df_all
            .sort_values("load_date", ascending=False)
            .drop_duplicates(subset=["city_id", "hotel_name"], keep="first")
        )

        #   4. Réécrire la table complète — nettoie au passage les doublons existants
        df_all.to_sql("hotels", engine, if_exists="replace", index=False)
        print(f"[OK] hotels — {len(df_all)} rows total ({len(df_new)} new/updated from {len(hotel_keys)} file(s))")
    else:
        print("[SKIP] no hotels files found in S3")

    print("Done.")
