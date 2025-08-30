# File: cleanup_collections.py

from pymilvus import utility, connections

# --- CONFIG ---
_HOST = '127.0.0.1'
_PORT = '19530'

# Danh sách các collection cần xóa
COLLECTIONS_TO_DELETE = [
    'video_retrieval_siglip',       # Tên collection IVF_FLAT
  # Tên collection HNW
]

# --- SCRIPT ---
def cleanup():
    print(f"Đang kết nối tới Milvus server...")
    connections.connect("default", host=_HOST, port=_PORT)
    
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