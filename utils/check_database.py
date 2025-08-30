from pymilvus import Collection, connections, utility

# --- CONFIG ---
_HOST = '127.0.0.1'
_PORT = '19530'
# Tên collection bạn muốn kiểm tra
_COLLECTION_NAME = 'video_retrieval_v3' 

# --- SCRIPT ---
print(f"Đang kết nối tới Milvus server...")
connections.connect("default", host=_HOST, port=_PORT)

# Kiểm tra collection có tồn tại không
if not utility.has_collection(_COLLECTION_NAME):
    print(f"Collection '{_COLLECTION_NAME}' không tồn tại.")
else:
    collection = Collection(_COLLECTION_NAME)
    collection.load()
    
    # Lấy 5 thực thể đầu tiên làm mẫu
    # expr="id >= 0" là một cách để lấy tất cả, rồi giới hạn bằng limit
    results = collection.query(
        expr="id >= 0",
        limit=5,
        # Chỉ lấy ra các trường này, không lấy embedding cho đỡ rối màn hình
        output_fields=["id", "path", "caption"] 
    )
    
    print(f"\n✅ Dưới đây là {len(results)} bản ghi đầu tiên trong collection '{_COLLECTION_NAME}':\n")
    for hit in results:
        # hit là một dictionary
        print(f"  ID      : {hit['id']}")
        print(f"  Path    : {hit['path']}")
        print(f"  Caption : {hit['caption'][:100]}...") # In 100 ký tự đầu của caption
        print("-" * 30)
    
    print(f"Tổng số thực thể trong collection: {collection.num_entities}")

connections.disconnect("default")