"""Rebuild FAISS index from existing uploaded images in the metadata database."""
import sqlite3
from pathlib import Path
from PIL import Image
import numpy as np

from app.config import DB_PATH, UPLOAD_DIR
from app.services.enhance import enhance_image
from app.services.dinov2 import extract_features
from app.services.vector_store import VectorStore
from app.services.metadata_store import MetadataStore

print("Rebuilding FAISS index from metadata database...")

# Load metadata
meta_store = MetadataStore()
rows = meta_store._conn.execute(
    "SELECT id, category, specification, image_path FROM metadata WHERE status = 'active'"
).fetchall()
print(f"Found {len(rows)} active records in metadata DB")

# Create new vector store
vs = VectorStore()

# Re-extract features for each image
for r in rows:
    id_ = r["id"]
    category = r["category"]
    # image_path is like /uploads/filename.jpg — resolve to actual file
    img_filename = r["image_path"].replace("/uploads/", "")
    img_path = UPLOAD_DIR / img_filename

    if not img_path.exists():
        print(f"  WARNING: image not found for id={id_}: {img_path}")
        continue

    print(f"  Processing id={id_}, category={category}, file={img_filename}")
    image = Image.open(img_path).convert("RGB")
    enhanced = enhance_image(image)
    features = extract_features(enhanced)
    vs.add(vector=features, id=id_, category=category)

# Save the rebuilt index
vs.save()
print(f"FAISS index rebuilt with {vs.get_total_count()} vectors, categories: {vs.get_categories()}")
print(f"Index saved to: {Path('data/faiss/index.faiss')}")

meta_store.close()