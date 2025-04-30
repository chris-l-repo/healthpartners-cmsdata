# download_hospital_datasets.py
import os
import json
import re
import requests
from io import StringIO
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

# CONFIGURATION
METASTORE_URL = 'https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items'
METADATA_FILE = 'last_runs.json'
OUTPUT_DIR = 'processed'
MAX_WORKERS = 4  # parallelism

# Helpers

def to_snake_case(s):
    s = re.sub(r"[^\w\s]", '', s)
    s = re.sub(r"\s+", '_', s)
    return s.lower()


def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE) as f:
            return json.load(f)
    return {}


def save_metadata(data):
    with open(METADATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def process_dataset(item, metadata):
    ds_id = item['identifier']
    modified = item.get('modified')
    last = metadata.get(ds_id)
    if last and last >= modified:
        return f"{ds_id}: no update"

    for dist in item.get('distribution', []):
        url = dist['downloadURL']
        r = requests.get(url)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
        df.rename(columns=lambda c: to_snake_case(c), inplace=True)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_path = os.path.join(OUTPUT_DIR, f"{ds_id}.csv")
        df.to_csv(out_path, index=False)

    metadata[ds_id] = modified
    return f"{ds_id}: processed {len(df)} rows"


def main():
    metadata = load_metadata()
    resp = requests.get(METASTORE_URL)
    resp.raise_for_status()
    items = resp.json()

    # filter for theme 'Hospitals'
    hospitals = [i for i in items if 'Hospitals' in i.get('theme', [])]

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for res in ex.map(lambda it: process_dataset(it, metadata), hospitals):
            print(res)
            results.append(res)

    save_metadata(metadata)

if __name__ == '__main__':
    main()
