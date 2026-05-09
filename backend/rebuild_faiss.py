"""Rebuild FAISS index from existing uploaded images - ONE BATCH build, not incremental."""
import sqlite3
from pathlib import Path
from PIL import Image
import numpy as np
import faiss

from app.config import DB_PATH, UPLOAD_DIR, DINOV2_FEATURE_DIM, FAISS_INDEX_PATH
from app.services.enhance import enhance_image
from app.services.dinov2 import extract_features

print("Rebuilding FAISS index (batch mode)...")

# Load metadata
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT id, category, specification, image_path FROM metadata WHERE status = 'active'"
).fetchall()
print(f"Found {len(rows)} active records")

# Extract features for all images first
all_ids = []
all_vectors = []
all_categories = {}

for r in rows:
    id_ = r["id"]
    category = r["category"]
    img_filename = r["image_path"].replace("/uploads/", "")
    img_path = UPLOAD_DIR / img_filename

    if not img_path.exists():
        print(f"  SKIP: {img_path} not found")
        continue

    print(f"  Processing id={id_}, {category}/{r['specification']}, {img_filename}")
    image = Image.open(img_path).convert("RGB")
    enhanced = enhance_image(image)
    features = extract_features(enhanced)

    all_ids.append(id_)
    all_vectors.append(features.astype(np.float32))
    if category not in all_categories:
        all_categories[category] = set()
    all_categories[category].add(id_)

# Build index in one batch
print(f"\nBuilding FAISS index with {len(all_vectors)} vectors...")
vectors_np = np.stack(all_vectors)
ids_np = np.array(all_ids, dtype=np.int64)

# Use IndexIDMap(IndexFlatL2) for small datasets
flat = faiss.IndexFlatL2(DINOV2_FEATURE_DIM)
index = faiss.IndexIDMap(flat)
index.add_with_ids(vectors_np, ids_np)

print(f"Index built: ntotal={index.ntotal}")
print(f"Categories: {list(all_categories.keys())}")

# Verify: search each vector should find itself at L2=0
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

# Save
faiss.write_index(index, str(FAISS_INDEX_PATH))
print(f"\nIndex saved to: {FAISS_INDEX_PATH}")
print(f"Total: {len(all_ids)} vectors, {len(all_categories)} categories")

conn.close()