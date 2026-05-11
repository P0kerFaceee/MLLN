"""Rebuild FAISS index from parts+photos tables — ONE BATCH build, compute initial distance stats."""
import sqlite3
import json
from pathlib import Path
from PIL import Image
import numpy as np
import faiss

from app.config import DB_PATH, UPLOAD_DIR, DINOV2_FEATURE_DIM, FAISS_INDEX_PATH
from app.services.enhance import enhance_image
from app.services.dinov2 import extract_features

print("Rebuilding FAISS index from parts+photos tables (batch mode)...")

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

photos = conn.execute(
    "SELECT p.id, p.part_id, p.image_path, p.angle, pt.category "
    "FROM photos p JOIN parts pt ON p.part_id = pt.id "
    "WHERE p.status = 'active' AND pt.status = 'active'"
).fetchall()
print(f"Found {len(photos)} active photos")

all_ids = []
all_vectors = []
all_categories = {}
photo_to_part = {}

for ph in photos:
    photo_id = ph["id"]
    category = ph["category"]
    img_filename = ph["image_path"].replace("/uploads/", "")
    img_path = UPLOAD_DIR / img_filename

    if not img_path.exists():
        print(f"  SKIP: {img_path} not found")
        continue

    print(f"  Processing photo_id={photo_id}, category={category}, {img_filename}")
    image = Image.open(img_path).convert("RGB")
    enhanced = enhance_image(image)
    features = extract_features(enhanced)

    all_ids.append(photo_id)
    all_vectors.append(features.astype(np.float32))
    if category not in all_categories:
        all_categories[category] = set()
    all_categories[category].add(photo_id)
    photo_to_part[photo_id] = ph["part_id"]

# Build index in one batch
print(f"\nBuilding FAISS index with {len(all_vectors)} vectors...")
vectors_np = np.stack(all_vectors)
ids_np = np.array(all_ids, dtype=np.int64)

flat = faiss.IndexFlatL2(DINOV2_FEATURE_DIM)
index = faiss.IndexIDMap(flat)
index.add_with_ids(vectors_np, ids_np)

print(f"Index built: ntotal={index.ntotal}")
print(f"Categories: {list(all_categories.keys())}")

# Verify
print("\nVerifying ID-vector mapping...")
errors = 0
for i, (id_, vec) in enumerate(zip(all_ids, all_vectors)):
    distances, result_ids = index.search(vec.reshape(1, -1).astype(np.float32), 1)
    found_id = int(result_ids[0][0])
    found_dist = float(distances[0][0])
    if found_id != id_ or found_dist != 0.0:
        print(f"  ERROR: id={id_} found as id={found_id} dist={found_dist}")
        errors += 1
if errors == 0:
    print("  All vectors verified OK!")
else:
    print(f"  {errors} errors found!")

# Compute pairwise L2 distances for initial stats
print("\nComputing initial distance statistics...")
n = len(all_vectors)
if n > 1:
    vecs = np.stack(all_vectors)
    # Compute all pairwise distances
    all_distances = []
    for i in range(n):
        diffs = vecs[i] - vecs
        dists = np.linalg.norm(diffs, axis=1)
        for j in range(n):
            if j != i:
                all_distances.append(dists[j])

    dist_arr = np.array(all_distances)
    dist_mean = float(dist_arr.mean())
    dist_std = float(dist_arr.std())
    dist_count = float(len(all_distances))

    print(f"  dist_mean = {dist_mean:.2f}")
    print(f"  dist_std  = {dist_std:.2f}")
    print(f"  dist_count = {dist_count}")

    conn.execute("INSERT OR REPLACE INTO stats_meta (key, value) VALUES (?, ?)", ("dist_mean", dist_mean))
    conn.execute("INSERT OR REPLACE INTO stats_meta (key, value) VALUES (?, ?)", ("dist_std", dist_std))
    conn.execute("INSERT OR REPLACE INTO stats_meta (key, value) VALUES (?, ?)", ("dist_count", dist_count))
    conn.commit()
    print("  Stats saved to stats_meta table")
else:
    print("  Too few vectors for stats, skipping")

# Save FAISS index
faiss.write_index(index, str(FAISS_INDEX_PATH))
print(f"\nIndex saved to: {FAISS_INDEX_PATH}")
print(f"Total: {len(all_ids)} vectors, {len(all_categories)} categories")

conn.close()