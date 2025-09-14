import os
import json
import numpy as np
from pymilvus import (
    connections,
    utility,
    FieldSchema, CollectionSchema, DataType,
    Collection,
)
from tqdm import tqdm

# ================= CONFIG =================

_HOST = '127.0.0.1'
_PORT = '19530'

# Collection name mới cho SigLip không có caption
_COLLECTION_NAME = 'SIGLIP_COLLECTION'
_ID_FIELD = 'id'
_VECTOR_FIELD = 'embedding'
_PATH_FIELD = 'path'

# Dimension của SigLip
_DIM = 1152

# L-packs để xử lý
# L-packs để xử lý (K01 -> K20)
L_PACKS_TO_PROCESS = [f"K{i:02d}" for i in range(1, 21)] + [f"L{i}" for i in range(21,31)]
_INDEX_TYPE = "HNSW"   
_INDEX_PARAMS = {
    "HNSW": {"M": 32, "efConstruction": 512},
    "FLAT": {},  # Flat không cần tham số
    "IVF_FLAT": {"nlist": 1024},
    "IVF_SQ8": {"nlist": 1024},
}
# Đường dẫn base
KEYFRAMES_BASE_DIR = "D:/Workplace/AIC_2025/Data/Keyframes"

FEATURES_BASE_DIR = "D:/Workplace/AIC_2025/Data/All_Features/SigLip"
MAPPING_BASE_DIR  = "D:/Workplace/AIC_2025/Data/All_Features/SigLip"

# Batch insert
BATCH_SIZE = 5000

# ================= HELPER =================

def normalize(vec):
    norm = np.linalg.norm(vec)
    if norm == 0 or np.isnan(norm):
        return np.zeros_like(vec, dtype=np.float32)
    return vec / norm

# ================= MAIN =================

def main():
    all_clean_data = []
    global_id_counter = 0

    print("\nStep 1: Process each L-pack...")
    for l_pack in L_PACKS_TO_PROCESS:
        print(f"\n--- Processing {l_pack} ---")

        features_path = os.path.join(FEATURES_BASE_DIR, f"{l_pack}_ViT-SO400M-14-SigLIP-384_features.npy")
        mapping_path  = os.path.join(MAPPING_BASE_DIR,  f"{l_pack}_ViT-SO400M-14-SigLIP-384_mapping.json")
        if not os.path.isfile(features_path) or not os.path.isfile(mapping_path):
            print(f"⚠️ Skip {l_pack}, missing features or mapping.")
            continue

        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        N = len(mapping)
        D = _DIM
        features = np.memmap(features_path, dtype=np.float32, mode="r", shape=(N, D))
        features = np.array([normalize(e) for e in features])

        # Duyệt từng entry trong mapping
        for abs_path, local_id in mapping.items():
            rel_path = os.path.relpath(abs_path, KEYFRAMES_BASE_DIR).replace("\\", "/")

            all_clean_data.append({
                "id": global_id_counter,
                "path": rel_path,
                "embedding": features[local_id],
            })
            global_id_counter += 1

        print(f"✅ {l_pack}: {len(mapping)} items processed.")

    num_clean_data = len(all_clean_data)
    if num_clean_data == 0:
        print("❌ No data to insert. Exit.")
        return

    print(f"\n✅ Finished. Total {num_clean_data} records.")

    # ================== INGEST TO MILVUS ==================

    print("\nStep 2: Connect to Milvus...")
    connections.connect("default", host=_HOST, port=_PORT)
    print("✅ Connected.")

    if utility.has_collection(_COLLECTION_NAME):
        print(f"Collection '{_COLLECTION_NAME}' exists. Dropping...")
        utility.drop_collection(_COLLECTION_NAME)

    print(f"Creating collection '{_COLLECTION_NAME}'...")
    field_id = FieldSchema(name=_ID_FIELD, dtype=DataType.INT64, is_primary=True, auto_id=False)
    field_path = FieldSchema(name=_PATH_FIELD, dtype=DataType.VARCHAR, max_length=1024)
    field_embedding = FieldSchema(name=_VECTOR_FIELD, dtype=DataType.FLOAT_VECTOR, dim=_DIM)

    schema = CollectionSchema(
        fields=[field_id, field_path, field_embedding],
        description="Collection for SigLip features (no captions)"
    )
    collection = Collection(name=_COLLECTION_NAME, schema=schema, consistency_level="Strong")
    print(f"✅ Collection '{_COLLECTION_NAME}' created.")

    print("Step 3: Insert data...")
    for i in tqdm(range(0, num_clean_data, BATCH_SIZE), desc="Inserting"):
        end = min(i + BATCH_SIZE, num_clean_data)
        batch = all_clean_data[i:end]

        entities = [
            [item['id'] for item in batch],
            [item['path'] for item in batch],
            [item['embedding'] for item in batch],
        ]
        collection.insert(entities)

    print("✅ Insert finished. Flushing...")
    collection.flush()
    print(f"✅ Flush done. Total entities: {collection.num_entities}")

    print("Step 4: Create index...")
    index_params = {"metric_type": "IP", "index_type": f"{_INDEX_TYPE}", "params": _INDEX_PARAMS.get(_INDEX_TYPE, {}) }
    collection.create_index(field_name=_VECTOR_FIELD, index_params=index_params)
    utility.wait_for_index_building_complete(_COLLECTION_NAME)
    print("✅ Index built.")

    collection.load()
    print("✅ Collection loaded and ready.")

    connections.disconnect("default")

if __name__ == "__main__":
    main()
