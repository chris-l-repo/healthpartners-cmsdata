# download_hospital_datasets.py
import os
import json
import re
import requests
from io import StringIO
import pandas as pd

# CONFIGURATION
METASTORE_URL = 'https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items'
METADATA_FILE = 'last_runs.json'
OUTPUT_DIR = 'processed'

# helper to convert headerss
def to_snake_case(text):
    # remove non-alphanumeric and spaces
    text = re.sub(r"[^\w\s]", "", text)
    text = text.replace(' ', '_')
    return text.lower()

# load last run times
if os.path.exists(METADATA_FILE):
    with open(METADATA_FILE) as meta_file:
        last_runs = json.load(meta_file)
else:
    last_runs = {}

# fetch metastore entries
resp = requests.get(METASTORE_URL)
resp.raise_for_status()
all_items = resp.json()

# filter for 'Hospitals'
hospitals = []
for entry in all_items:
    themes = entry.get('theme', [])
    if 'Hospitals' in themes:
        hospitals.append(entry)

# process each dataset
for item in hospitals:
    ds_id = item['identifier']
    modified = item.get('modified')
    if last_runs.get(ds_id) == modified:
        print(f"{ds_id}: no update")
        continue

    distributions = item.get('distribution', [])
    for dist in distributions:
        url = dist.get('downloadURL')
        r = requests.get(url)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
        # rename columns
        new_cols = {}
        for col in df.columns:
            new_cols[col] = to_snake_case(col)
        df = df.rename(columns=new_cols)

        # save output
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_file = os.path.join(OUTPUT_DIR, f"{ds_id}.csv")
        df.to_csv(out_file, index=False)
        print(f"{ds_id}: processed {len(df)} rows")

    last_runs[ds_id] = modified

# save updated metadata
with open(METADATA_FILE, 'w') as meta_file:
    json.dump(last_runs, meta_file, indent=2)