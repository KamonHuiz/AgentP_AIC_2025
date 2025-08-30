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
_COLLECTION_NAME = 'video_retrieval_v3_hnsw' # Thêm suffix _hnsw
_ID_FIELD = 'id'
_VECTOR_FIELD = 'embedding'
_PATH_FIELD = 'path'
_CAPTION_FIELD = 'caption'

# 3. Thông số của dữ liệu
_DIM = 768

# 4. DANH SÁCH CÁC GÓI L CẦN XỬ LÝ
#L_PACKS_TO_PROCESS = [f"L{i}" for i in range(21, 31)] # ['L21', 'L22', ..., 'L30']
L_PACKS_TO_PROCESS = [f"L{i}" for i in range(21, 22)] # ['L21', 'L22', ..., 'L30']

# 5. Đường dẫn tới các thư mục và file dữ liệu
KEYFRAMES_BASE_DIR = "D:/Workplace/AIC_2025/Data/Keyframes"
FEATURES_BASE_DIR = "D:/Workplace/AIC_2025/Data/All_Features/OpenCLIP_L14"
CAPTIONS_PATH = "D:/Workplace/AIC_2025/Data/All_Features/BLIP/captions_blip2_flan_t5.json"

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
        print(paths_in_pack[0:10])             
    connections.connect("default", host="127.0.0.1", port="19530")

# Liệt kê tất cả collection
    print("Collections hiện có:", utility.list_collections())

    # Kiểm tra từng collection
    for col_name in utility.list_collections():
        col = Collection(col_name)
        print(f"Collection: {col_name}, số entity: {col.num_entities}")

# Kết nối tới Milvus

main()