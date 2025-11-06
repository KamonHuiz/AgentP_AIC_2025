# File: cleanup_collections.py

from pymilvus import utility, connections

# --- CONFIG ---
_HOST = '127.0.0.1'
_PORT = '19530'
COLLECTION_HNSW_OPENCLIP = 'video_retrieval_final'
COLLECTION_HNSW_SIGLIP = 'video_retrieval_siglip'
COLLECTION_HNSW_APPLE = 'video_retrieval_apple'
COLLECTION_HNSW_SIGLIP_NOCAP = "video_retrieval_siglip_nocap"
# Danh sách các collection cần xóa
COLLECTIONS_TO_DELETE = ['video_retrieval_v3_hnsw', 'video_retrieval_final', 'video_retrieval_apple', 'video_retrieval_siglip']

# --- SCRIPT ---
def cleanup():
    print(f"Đang kết nối tới Milvus server...")
    connections.connect("default", host=_HOST, port=_PORT)
    collections = utility.list_collections()
    print("Collections hiện tại:", collections)

    for name in COLLECTIONS_TO_DELETE:
        print(f"Kiểm tra collection '{name}'...")
        if utility.has_collection(name):
            print(f"--> Đang xóa collection '{name}'...")
            utility.drop_collection(name)
            print(f"--> ✅ Đã xóa thành công.")
        else:
            print(f"--> Collection '{name}' không tồn tại, bỏ qua.")
            
    connections.disconnect("default")
    print("\nDọn dẹp hoàn tất!")

if __name__ == '__main__':
    cleanup()