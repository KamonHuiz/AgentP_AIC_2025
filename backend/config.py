# config.py

# --- Cấu hình Web App ---
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True

# --- Cấu hình Model & Dữ liệu ---
IMAGE_BASE_PATH = "D:/Workplace/AIC_2025/Data" # Thư mục gốc chứa thư mục Keyframes

MODEL_NAME_OPENCLIP = 'ViT-L-14'
PRETRAINED_OPENCLIP = 'datacomp_xl_s13b_b90k'

MODEL_NAME_SIGLIP = 'ViT-SO400M-14-SigLIP-384'
PRETRAINED_SIGLIP = 'webli'

MODEL_NAME_APPLE = 'hf-hub:apple/DFN5B-CLIP-ViT-H-14-384'



# --- Cấu hình Milvus MỚI ---
MILVUS_HOST = '127.0.0.1'
MILVUS_PORT = '19530'
# Tên 3 collection chúng ta đã tạo

COLLECTION_HNSW_FINAL_FIRST_G = "SIGLIP_COLLECTION" 

# --- Cấu hình Tìm kiếm & Rerank MỚI ---
# Top K kết quả lấy từ Milvus để đưa vào rerank

# Trọng số cho điểm CLIP trong công thức Hybrid Score. 
# 0.6 nghĩa là 60% tin vào CLIP, 40% tin vào BM25.
ALPHA = 0.6