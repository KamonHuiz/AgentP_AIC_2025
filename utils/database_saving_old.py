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

# Collection name cho SigLip
_COLLECTION_NAME = 'video_retrieval_siglip'
_ID_FIELD = 'id'
_VECTOR_FIELD = 'embedding'
_PATH_FIELD = 'path'
_CAPTION_FIELD = 'caption'

# Dimension của SigLip
_DIM = 1152

# L-packs để xử lý
L_PACKS_TO_PROCESS = [f"L{i}" for i in range(21, 31)]

# Đường dẫn base
KEYFRAMES_BASE_DIR = "D:/Workplace/AIC_2025/Data/Keyframes"

# SigLip
#FEATURES_BASE_DIR = "D:/Workplace/AIC_2025/Data/All_Features/SigLip"
#MAPPING_BASE_DIR  = "D:/Workplace/AIC_2025/Data/All_Features/SigLip"

# Apple (comment lại, sau khi test SigLip thì đổi qua Apple)
FEATURES_BASE_DIR = "D:\Workplace\AIC_2025\Data\All_Features\SigLip"
MAPPING_BASE_DIR  = "D:\Workplace\AIC_2025\Data\All_Features\SigLip"

# Caption chung
CAPTIONS_PATH = "D:/Workplace/AIC_2025/Data/All_Features/BLIP/captions_blip2_flan_t5.json"

# Batch insert
BATCH_SIZE = 1152

# ================= HELPER =================

def normalize(vec):
    norm = np.linalg.norm(vec)  # tính độ dài vector
    if norm == 0 or np.isnan(norm):  
        # nếu vector rỗng (toàn số 0) hoặc bản thân norm bị NaN
        return np.zeros_like(vec, dtype=np.float32)  
        # trả về vector toàn số 0, vẫn đúng dimension
    return vec / norm  # còn lại thì chuẩn hóa bình thường

# ================= MAIN =================

def main():
    print("Step 1: Load captions...")
    with open(CAPTIONS_PATH, "r", encoding='utf-8') as f:
        captions_dict = json.load(f)
    print(f"✅ Loaded {len(captions_dict)} captions.")

    all_clean_data = []
    global_id_counter = 0

    print("\nStep 2: Process each L-pack...")
    for l_pack in L_PACKS_TO_PROCESS:
        print(f"\n--- Processing {l_pack} ---")

        features_path = os.path.join(FEATURES_BASE_DIR, f"{l_pack}_SigLIP_features.npy")
        mapping_path  = os.path.join(MAPPING_BASE_DIR,  f"{l_pack}_SigLIP_mapping.json")

        if not os.path.isfile(features_path) or not os.path.isfile(mapping_path):
            print(f"⚠️ Skip {l_pack}, missing features or mapping.")
            continue
        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        # Load features
        #features = np.load(features_path, mmap_mode="r")
        N = len(mapping)   # số vector
        D = _DIM           # 1024 cho SigLIP

        features = np.memmap(features_path, dtype=np.float32, mode="r", shape=(N, D))
        features = np.array([normalize(e) for e in features])

        # Load mapping


        # Duyệt từng entry trong mapping
        for abs_path, local_id in mapping.items():
            rel_path = os.path.relpath(abs_path, KEYFRAMES_BASE_DIR).replace("\\", "/")

            if rel_path not in captions_dict:
                continue

            all_clean_data.append({
                "id": global_id_counter,
                "path": rel_path,
                "embedding": features[local_id],
                "caption": captions_dict[rel_path]
            })
            global_id_counter += 1

        print(f"✅ {l_pack}: {len(mapping)} items processed.")

    num_clean_data = len(all_clean_data)
    if num_clean_data == 0:
        print("❌ No clean data to insert. Exit.")
        return

    print(f"\n✅ Finished. Total {num_clean_data} records.")

    # ================== INGEST TO MILVUS ==================

    print("\nStep 3: Connect to Milvus...")
    connections.connect("default", host=_HOST, port=_PORT)
    print("✅ Connected.")

    if utility.has_collection(_COLLECTION_NAME):
        print(f"Collection '{_COLLECTION_NAME}' exists. Dropping...")
        utility.drop_collection(_COLLECTION_NAME)

    print(f"Creating collection '{_COLLECTION_NAME}'...")
    field_id = FieldSchema(name=_ID_FIELD, dtype=DataType.INT64, is_primary=True, auto_id=False)
    field_path = FieldSchema(name=_PATH_FIELD, dtype=DataType.VARCHAR, max_length=1024)
    field_caption = FieldSchema(name=_CAPTION_FIELD, dtype=DataType.VARCHAR, max_length=2048)
    field_embedding = FieldSchema(name=_VECTOR_FIELD, dtype=DataType.FLOAT_VECTOR, dim=_DIM)

    schema = CollectionSchema(
        fields=[field_id, field_path, field_caption, field_embedding],
        description="Collection for Apple features"
    )
    collection = Collection(name=_COLLECTION_NAME, schema=schema, consistency_level="Strong")
    print(f"✅ Collection '{_COLLECTION_NAME}' created.")

    print("Step 4: Insert data...")
    for i in tqdm(range(0, num_clean_data, BATCH_SIZE), desc="Inserting"):
        end = min(i + BATCH_SIZE, num_clean_data)
        batch = all_clean_data[i:end]

        entities = [
            [item['id'] for item in batch],
            [item['path'] for item in batch],
            [item['caption'] for item in batch],
            [item['embedding'] for item in batch],
        ]
        collection.insert(entities)

    print("✅ Insert finished. Flushing...")
    collection.flush()
    print(f"✅ Flush done. Total entities: {collection.num_entities}")

    print("Step 5: Create index...")
    index_params = {"metric_type": "IP", "index_type": "HNSW", "params": {"M": 32, "efConstruction": 512}}
    collection.create_index(field_name=_VECTOR_FIELD, index_params=index_params)
    utility.wait_for_index_building_complete(_COLLECTION_NAME)
    print("✅ Index built.")

    collection.load()
    print("✅ Collection loaded and ready.")

    connections.disconnect("default")

if __name__ == "__main__":
    main()
