import os
import re
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from rank_bm25 import BM25Okapi # Import thư viện BM25

from src import RetrievalSystem
import config

# --- HELPER FUNCTION ---
def normalize_scores(scores):
    """Chuẩn hóa một danh sách điểm số về dải 0-1."""
    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        return [1.0 for _ in scores]
    return [(score - min_score) / (max_score - min_score) for score in scores]

# --- KHỞI TẠO HỆ THỐNG (LOGIC MỚI) ---
print("--- Starting Application ---")
# 1. Khởi tạo hệ thống tìm kiếm bằng Milvus
retrieval_service = RetrievalSystem(
    model_name=config.MODEL_NAME,
    pretrained=config.PRETRAINED,
    milvus_host=config.MILVUS_HOST,
    milvus_port=config.MILVUS_PORT,
    collection_name_hnsw=config.COLLECTION_HNSW
)
# 2. Hệ thống lọc màu (tạm thời không dùng đến nhưng vẫn có thể giữ lại)
# color_filter_service = ...
print("--- Application Started ---")


# --- KHỞI TẠO ỨNG DỤNG WEB ---
app = Flask(__name__, template_folder="../frontend", static_folder="../frontend")
CORS(app)

# (Hàm get_video_id_from_path và route '/' giữ nguyên như cũ)
def get_video_id_from_path(path):
    match = re.search(r'(L\d+/V\d+)', path.replace('\\', '/'))
    return match.group(1) if match else None

@app.route('/')
def index():
    return render_template('index.html')

# === ROUTE TÌM KIẾM ĐÃ ĐƯỢC NÂNG CẤP TOÀN DIỆN ===@app.route('/search', methods=['GET'])
# File: app.py

# ... (các phần import và khởi tạo giữ nguyên) ...

# === THAY THẾ TOÀN BỘ HÀM NÀY BẰNG PHIÊN BẢN MỚI ===
@app.route('/search', methods=['GET'])
def search_endpoint():
    try:
        # --- A. LẤY THAM SỐ & CHỌN INDEX ---
        query = request.args.get('query')
        if not query:
            return jsonify({"error": "Thiếu tham số 'query'."}), 400
        
        # ===> THAY ĐỔI 1: ĐỌC K TRỰC TIẾP TỪ URL <===
        # Lấy giá trị k từ URL, đặt giá trị mặc định là 50 nếu không có.
        # Chuyển đổi sang kiểu int.
        k_value = int(request.args.get('k', 500))
        ef_value = k_value +400
        search_params = {"params": {"ef": ef_value}}
        

        # --- B. GIAI ĐOẠN 1: TRUY VẤN VECTOR (RETRIEVAL) ---
        initial_results = retrieval_service.search(
            query=query, 
            k=k_value, # Sử dụng k_value lấy từ URL
            search_params=search_params
        )
        if not initial_results:
            return jsonify({"frame_results": [], "video_results": []})

        # --- C. GIAI ĐOẠN 2: RERANKING VỚI BM25 ---
        # ... (phần còn lại của hàm giữ nguyên như cũ) ...
        
        paths = [res[0] for res in initial_results]
        clip_scores = [res[1] for res in initial_results]
        captions = [res[2] for res in initial_results]
        
        tokenized_captions = [caption.split() for caption in captions]
        bm25 = BM25Okapi(tokenized_captions)
        
        tokenized_query = query.split()
        bm25_scores = bm25.get_scores(tokenized_query)

        norm_clip_scores = normalize_scores(clip_scores)
        norm_bm25_scores = normalize_scores(bm25_scores)
        
        reranked_results = []
        for i in range(len(paths)):
           
            #
            final_score = config.ALPHA * norm_clip_scores[i] + (1 - config.ALPHA) * norm_bm25_scores[i]
            reranked_results.append({ "path": paths[i], "score": final_score })
            
        reranked_results.sort(key=lambda x: x['score'], reverse=True)
        
        # --- D. CHUẨN BỊ DỮ LIỆU TRẢ VỀ ---
        # ... (phần này giữ nguyên như cũ) ...
        final_paths_with_scores = reranked_results
        path_to_score_map = {item['path']: item['score'] for item in final_paths_with_scores}
        final_paths = [item['path'] for item in final_paths_with_scores]

        frame_results = []
        for path in final_paths:
            score = path_to_score_map.get(path, 0)
            #print(f"Đây là Path {path}, score:{score}")
            frame_results.append({ "path": f"/images/Keyframes/{path}", "score": score })

        videos_data = {}
        for rank, path in enumerate(final_paths):
            video_id = get_video_id_from_path(path)
            if not video_id: continue
            if video_id not in videos_data:
                videos_data[video_id] = { "frames": [], "best_rank": rank, "video_score": path_to_score_map.get(path, 0) }
            videos_data[video_id]['frames'].append(path)

        video_results_list = []
        for video_id, data in videos_data.items():
            video_frames = []
            for path in data['frames']:
                score = path_to_score_map.get(path, 0)
                video_frames.append({ "path": f"/images/Keyframes/{path}", "score": score })
            video_results_list.append({ "video_id": video_id, "video_score": data['video_score'], "best_rank": data['best_rank'], "frames": video_frames })
        video_results_list.sort(key=lambda x: x['best_rank'])

        return jsonify({ "frame_results": frame_results, "video_results": video_results_list })

    except Exception as e:
        print(f"An error occurred in /search endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Đã có lỗi xảy ra trên server."}), 500
# === ROUTE PHỤC VỤ ẢNH (CÓ CHÚT THAY ĐỔI NHỎ) ===
@app.route('/images/<path:filename>')
def serve_image(filename):
    # filename giờ sẽ có dạng Keyframes/L21/L21_V001/000000.webp
    return send_from_directory(config.IMAGE_BASE_PATH, filename)

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)