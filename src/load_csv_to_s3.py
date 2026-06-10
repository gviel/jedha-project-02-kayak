#!/usr/bin/env python
# coding: utf-8

# KAYAK project phase 5 : upload processed CSVs to S3 data lake
# Reads data/csv/, uploads each file to s3://<S3_BUCKET>/<S3_PREFIX>/<YYYYMMDD>/<filename>

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID     = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_REGION            = os.environ.get("AWS_REGION", "eu-west-3")
S3_BUCKET             = os.environ["S3_BUCKET"]
S3_PREFIX             = os.environ.get("S3_PREFIX", "csv/")
LOCAL_RETENTION_DAYS  = int(os.environ.get("LOCAL_RETENTION_DAYS", "7"))

DATA_DIR_CSV = Path("data/csv")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

if __name__ == "__main__":
    # cities.csv — fichier de référence, uploadé à la racine du préfixe S3 (pas de date-dir)
    cities_file = DATA_DIR_CSV / "cities.csv"
    if cities_file.exists():
        key = f"{S3_PREFIX}cities.csv"
        s3.upload_file(str(cities_file), S3_BUCKET, key)
        print(f"[OK] s3://{S3_BUCKET}/{key}")

    # files = sorted(DATA_DIR_CSV.glob("[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]/*.csv"))
    # glob */*.csv puis filtre les répertoires dont le nom est exactement 8 chiffres
    files = [f for f in sorted(DATA_DIR_CSV.glob("*/*.csv")) if re.match(r"\d{8}$", f.parent.name)]

    if not files and not cities_file.exists():
        print("No CSV files found in data/csv/ — run the pipeline first.")
        raise SystemExit(1)

    for fpath in files:
        m = re.search(r"\d{8}", fpath.name)
        date_dir = m.group() if m else datetime.now().strftime("%Y%m%d")
        key = f"{S3_PREFIX}{date_dir}/{fpath.name}"
        s3.upload_file(str(fpath), S3_BUCKET, key)
        print(f"[OK] s3://{S3_BUCKET}/{key}")

    print(f"Done — {len(files)} file(s) uploaded.")

    # Rétention locale : conserver les LOCAL_RETENTION_DAYS répertoires datés les plus récents
    dated_dirs = sorted(
        [d for d in DATA_DIR_CSV.iterdir() if d.is_dir() and re.match(r"\d{8}$", d.name)],
        reverse=True,  # plus récent en premier
    )
    removed = 0
    for d in dated_dirs[LOCAL_RETENTION_DAYS:]:
        shutil.rmtree(d)
        print(f"[CLEANUP] {d} supprimé")
        removed += 1
    if removed:
        print(f"[CLEANUP] {removed} répertoire(s) purgé(s) (rétention : {LOCAL_RETENTION_DAYS} derniers jours avec données)")
