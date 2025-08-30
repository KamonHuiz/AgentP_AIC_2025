import os
import re
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from rank_bm25 import BM25Okapi

from src import RetrievalSystem, RetrievalSystemApple
import config

# --- HELPER FUNCTION ---
def normalize_scores(scores):
    """Chuẩn hóa một danh sách điểm số về dải 0-1."""
    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        return [1.0 for _ in scores]
    return [(score - min_score) / (max_score - min_score) for score in scores]

print("--- Starting Application ---")

# --- Khởi tạo 3 retrievers ---
retrieval_service_openclip = RetrievalSystem(
    model_name=config.MODEL_NAME_OPENCLIP,
    pretrained=config.PRETRAINED_OPENCLIP,
    milvus_host=config.MILVUS_HOST,
    milvus_port=config.MILVUS_PORT,
    collection_name_hnsw=config.COLLECTION_HNSW_OPENCLIP
)

retrieval_service_siglip = RetrievalSystem(
    model_name=config.MODEL_NAME_SIGLIP,
    pretrained=config.PRETRAINED_SIGLIP,
    milvus_host=config.MILVUS_HOST,
    milvus_port=config.MILVUS_PORT,
    collection_name_hnsw=config.COLLECTION_HNSW_SIGLIP
)

retrieval_service_apple = RetrievalSystemApple(
    model_name=config.MODEL_NAME_APPLE,
    milvus_host=config.MILVUS_HOST,
    milvus_port=config.MILVUS_PORT,
    collection_name_hnsw=config.COLLECTION_HNSW_APPLE
)

print("--- Application Started ---")

app = Flask(__name__)
CORS(app)

def get_video_id_from_path(path: str):
    """
    Trích xuất 'Lxx_Vyyy' ở bất kỳ đâu trong path.
    Ví dụ: 'L21/L21_V001/000000.webp' -> 'L21_V001'
    """
    safe = path.replace("\\", "/")
    m = re.search(r"(L\d+_V\d+)", safe)
    return m.group(1) if m else None

@app.route("/search", methods=["GET"])
def search_endpoint():
    try:
        # --- A. Params ---
        query = request.args.get("query")
        if not query:
            return jsonify({"error": "Thiếu tham số 'query'."}), 400

        k_value = int(request.args.get("k", 500))
        ef_value = k_value + 400
        search_params = {"params": {"ef": ef_value}}

        # --- B. Chọn retriever theo mode ---
        mode = request.args.get("mode", "apple")  # default = apple
        if mode == "openclip":
            retriever = retrieval_service_openclip
        elif mode == "siglip":
            retriever = retrieval_service_siglip
        elif mode == "apple":
            retriever = retrieval_service_apple
        else:
            return jsonify({"error": f"Unknown mode: {mode}"}), 400

        # --- C. Vector search ---
        initial_results = retriever.search(
            query=query,
            k=k_value,
            search_params=search_params
        )
        if not initial_results:
            return jsonify({"frame_results": [], "video_results": []})

        # --- D. BM25 rerank ---
        paths = [res[0] for res in initial_results]
        clip_scores = [res[1] for res in initial_results]
        captions = [res[2] for res in initial_results]

        tokenized_captions = [c.split() for c in captions]
        bm25 = BM25Okapi(tokenized_captions)
        tokenized_query = query.split()
        bm25_scores = bm25.get_scores(tokenized_query)

        norm_clip_scores = normalize_scores(clip_scores)
        norm_bm25_scores = normalize_scores(bm25_scores)

        reranked_results = []
        for i in range(len(paths)):
            final_score = config.ALPHA * norm_clip_scores[i] + (1 - config.ALPHA) * norm_bm25_scores[i]
            reranked_results.append({"path": paths[i], "score": final_score})
        reranked_results.sort(key=lambda x: x["score"], reverse=True)

        # --- E. Chuẩn bị dữ liệu trả về ---
        path_to_score_map = {item["path"]: item["score"] for item in reranked_results}
        final_paths = [item["path"] for item in reranked_results]

        # 1) frame_results
        frame_results = []
        for path in final_paths:
            score = path_to_score_map.get(path, 0)
            frame_results.append({
                "path": f"/images/Keyframes/{path}",
                "score": score
            })

        # 2) group theo video
        videos_data = {}
        for rank, path in enumerate(final_paths):
            video_id = get_video_id_from_path(path)
            if not video_id:
                continue
            if video_id not in videos_data:
                videos_data[video_id] = {
                    "frames": [],
                    "best_rank": rank,
                    "video_score": path_to_score_map.get(path, 0)
                }
            videos_data[video_id]["frames"].append(path)

        # 3) build video_results + all_frames
        video_results_list = []
        for video_id, data in videos_data.items():
            video_frames = []
            for p in data["frames"]:
                score = path_to_score_map.get(p, 0)
                video_frames.append({
                    "path": f"/images/Keyframes/{p}",
                    "score": score
                })

            level_dir = video_id.split("_")[0]
            video_dir = os.path.join(config.IMAGE_BASE_PATH, "Keyframes", level_dir, video_id)
            all_frames = []
            if os.path.exists(video_dir):
                for fname in sorted(os.listdir(video_dir)):
                    if fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        rel_path = f"/images/Keyframes/{level_dir}/{video_id}/{fname}"
                        all_frames.append(rel_path)

            video_results_list.append({
                "video_id": video_id,
                "video_score": data["video_score"],
                "best_rank": data["best_rank"],
                "frames": video_frames,
                "all_frames": all_frames
            })

        video_results_list.sort(key=lambda x: x["best_rank"])

        return jsonify({
            "frame_results": frame_results,
            "video_results": video_results_list
        })

    except Exception as e:
        print(f"An error occurred in /search endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Đã có lỗi xảy ra trên server."}), 500

@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(config.IMAGE_BASE_PATH, filename)
if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=False)
