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
from natsort import natsorted

# --- CONFIG - VUI LÒNG KIỂM TRA VÀ CHỈNH SỬA CÁC THAM SỐ NÀY ---

# 1. Thông tin kết nối Milvus
_HOST = '127.0.0.1'
_PORT = '19530'

# 2. Thông tin Collection
#_COLLECTION_NAME = 'video_retrieval_v3'
_COLLECTION_NAME = 'video_retrieval_final' # Thêm suffix _hnsw
_ID_FIELD = 'id'
_VECTOR_FIELD = 'embedding'
_PATH_FIELD = 'path'
_CAPTION_FIELD = 'caption'

# 3. Thông số của dữ liệu
_DIM = 768

# 4. DANH SÁCH CÁC GÓI L CẦN XỬ LÝ
L_PACKS_TO_PROCESS = [f"L{i}" for i in range(21, 31)] # ['L21', 'L22', ..., 'L30']

# 5. Đường dẫn tới các thư mục và file dữ liệu
KEYFRAMES_BASE_DIR = "D:/Workplace/AIC_2025/Data/Keyframes"
FEATURES_BASE_DIR = "D:/Workplace/AIC_2025/Data/All_Features/OpenCLIP_L14"
CAPTIONS_PATH = "D:/Workplace/AIC_2025/Data/All_Features/BLIP/captions_blip2_flan_t5.json"
def normalize(vec):
    return vec / np.linalg.norm(vec)
# 6. Cấu hình khác
BATCH_SIZE = 1024

# --- SCRIPT CHÍNH ---

def main():
    # --- CÔNG ĐOẠN 1: CHUẨN BỊ DỮ LIỆU ---

    print("Bước 1: Tải file caption chung...")
    with open(CAPTIONS_PATH, "r", encoding='utf-8') as f:
        captions_dict = json.load(f)
    print(f"✅ Tải thành công {len(captions_dict)} captions.")

    all_clean_data = []
    global_id_counter = 0

    print("\nBước 2: Bắt đầu xử lý tuần tự từng gói L...")
    for l_pack in L_PACKS_TO_PROCESS:
        print(f"\n--- Đang xử lý gói: {l_pack} ---")

        keyframes_dir_for_pack = os.path.join(KEYFRAMES_BASE_DIR, l_pack)
        features_path_for_pack = os.path.join(FEATURES_BASE_DIR, f"{l_pack}_features.npy")

        if not os.path.isdir(keyframes_dir_for_pack) or not os.path.isfile(features_path_for_pack):
            print(f"⚠️  Cảnh báo: Bỏ qua {l_pack} vì không tìm thấy thư mục keyframes hoặc file features.")
            continue

        paths_in_pack = []
        for root, _, files in os.walk(keyframes_dir_for_pack):
            for file in files:
                if file.endswith(".webp"):
                    paths_in_pack.append(os.path.join(root, file))
        
        sorted_paths_in_pack = natsorted(paths_in_pack)
        
        embeddings_in_pack = np.load(features_path_for_pack)
        embeddings_in_pack = np.array([normalize(e) for e in embeddings_in_pack])
        if len(sorted_paths_in_pack) != len(embeddings_in_pack):
            print(f"❌ Lỗi: Số lượng ảnh ({len(sorted_paths_in_pack)}) và vector ({len(embeddings_in_pack)}) không khớp cho {l_pack}. Bỏ qua gói này.")
            continue
        
        print(f"Tìm thấy {len(sorted_paths_in_pack)} ảnh và vector {len(embeddings_in_pack)}tương ứng cho {l_pack}.")

        for i in range(len(sorted_paths_in_pack)):
            full_path = sorted_paths_in_pack[i]
            embedding = embeddings_in_pack[i]
            
            relative_path = os.path.relpath(full_path, KEYFRAMES_BASE_DIR).replace('\\', '/')
            
            if relative_path in captions_dict:
                all_clean_data.append({
                    "id": global_id_counter,
                    "path": relative_path,
                    "embedding": embedding,
                    "caption": captions_dict[relative_path]
                })
                global_id_counter += 1
    
    num_clean_data = len(all_clean_data)
    if num_clean_data == 0:
        print("❌ Không tìm thấy dữ liệu sạch nào để nạp. Dừng chương trình.")
        return
        
    print(f"\n✅ Xử lý hoàn tất. Tổng cộng có {num_clean_data} bản ghi sạch từ tất cả các gói.")

    # --- CÔNG ĐOẠN 2: NẠP DỮ LIỆU VÀO MILVUS ---
    
    print(f"\nBước 3: Đang kết nối tới Milvus server...")
    connections.connect("default", host=_HOST, port=_PORT)
    print("✅ Kết nối thành công.")
    
    if utility.has_collection(_COLLECTION_NAME):
        print(f"Collection '{_COLLECTION_NAME}' đã tồn tại. Sẽ xóa và tạo lại.")
        utility.drop_collection(_COLLECTION_NAME)
        
    print(f"Đang tạo collection '{_COLLECTION_NAME}'...")
    field_id = FieldSchema(name=_ID_FIELD, dtype=DataType.INT64, is_primary=True, auto_id=False)
    field_path = FieldSchema(name=_PATH_FIELD, dtype=DataType.VARCHAR, max_length=1024)
    field_caption = FieldSchema(name=_CAPTION_FIELD, dtype=DataType.VARCHAR, max_length=2048)
    field_embedding = FieldSchema(name=_VECTOR_FIELD, dtype=DataType.FLOAT_VECTOR, dim=_DIM)
    
    schema = CollectionSchema(
        fields=[field_id, field_path, field_caption, field_embedding],
        description="Collection for hybrid video retrieval system"
    )
    collection = Collection(name=_COLLECTION_NAME, schema=schema, consistency_level="Strong")
    print(f"✅ Đã tạo collection '{_COLLECTION_NAME}'.")

    print("Bước 4: Bắt đầu nạp dữ liệu vào Milvus...")
    for i in tqdm(range(0, num_clean_data, BATCH_SIZE), desc="Ingesting data"):
        end = min(i + BATCH_SIZE, num_clean_data)
        
        # ===> SỬA LỖI TẠI ĐÂY: Dùng đúng tên biến là `all_clean_data` <===
        batch_data = all_clean_data[i:end]
        
        entities = [
            [item['id'] for item in batch_data],
            [item['path'] for item in batch_data],
            [item['caption'] for item in batch_data],
            [item['embedding'] for item in batch_data]
        ]
        #print(collection.schema)

        collection.insert(entities)
    
    print("\n✅ Nạp dữ liệu thành công. Đang flush...")
    collection.flush()
    print(f"✅ Flush hoàn tất. Tổng số thực thể: {collection.num_entities}")
    print(f"Tong số ảnh: {num_clean_data}")
    print("Bước 5: Đang tạo index cho vector...")

    index_params = {"metric_type": "IP","index_type": "HNSW", "params": {"M": 32, "efConstruction": 512}}
    collection.create_index(field_name=_VECTOR_FIELD, index_params=index_params)
    utility.wait_for_index_building_complete(_COLLECTION_NAME)
    print("✅ Index đã được tạo thành công.")
    
    collection.load()
    print("✅ Collection đã được tải vào bộ nhớ và sẵn sàng để truy vấn.")
    connections.disconnect("default")

if __name__ == '__main__':
    main()