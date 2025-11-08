import os
import re
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from rank_bm25 import BM25Okapi
import requests
# IMPORT NOTE: thêm class mới vào src và import nó
from src import RetrievalSystemSiglipNoCap, OCRRetrievalES, SpeechRetrievalES
import config
from googletrans import Translator

class TranslatorModule:
    def __init__(self):
        self.translator = Translator()
    def translate(self, text):
        translated = self.translator.translate(text,src='vi',dest='en')
        return translated.text
    

# --- HELPER FUNCTION ---
def normalize_scores(scores):
    """Chuẩn hóa một danh sách điểm số về dải 0-1."""
    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        return [1.0 for _ in scores]
    return [(score - min_score) / (max_score - min_score) for score in scores]

print("--- Starting Application ---")

# --- Khởi tạo retrievers ---
# retrieval_service_openclip = RetrievalSystem(
#     model_name=config.MODEL_NAME_OPENCLIP,
#     pretrained=config.PRETRAINED_OPENCLIP,
#     milvus_host=config.MILVUS_HOST,
#     milvus_port=config.MILVUS_PORT,
#     collection_name_hnsw=config.COLLECTION_HNSW_OPENCLIP
# )

# retrieval_service_siglip = RetrievalSystem(
#     model_name=config.MODEL_NAME_SIGLIP,
#     pretrained=config.PRETRAINED_SIGLIP,
#     milvus_host=config.MILVUS_HOST,
#     milvus_port=config.MILVUS_PORT,
#     collection_name_hnsw=config.COLLECTION_HNSW_SIGLIP
# )
OCR_JSON_DIR = r"D:\Workplace\AIC_2025\Data\AUDIO_RECOGNIZATION"
translator_module = TranslatorModule()

# --- new: SigLip no-caption retriever (class bạn đã viết) ---
retrieval_service_siglip_nocap = RetrievalSystemSiglipNoCap(
    model_name=config.MODEL_NAME_SIGLIP,
    pretrained=config.PRETRAINED_SIGLIP,
    milvus_host=config.MILVUS_HOST,
    milvus_port=config.MILVUS_PORT,
    collection_name_hnsw=config.COLLECTION_HNSW_FINAL_FIRST_G  # cần có trong config
)
ocr_retriever = OCRRetrievalES(
        ocr_json_dir=OCR_JSON_DIR,
        host="http://localhost:9200",
        index_name="ocr_index_main",
        load_data=False)
AUDIO_DIR = r"D:\Workplace\AIC_2025\Data\AUDIO_RECOGNIZATION"
KEYFRAME_DIR = r"D:\Workplace\AIC_2025\Data\Keyframes"
audio_retriever = SpeechRetrievalES(
        context_json_dir=AUDIO_DIR,
        base_keyframe_dir=KEYFRAME_DIR,
        host="http://localhost:9200",
        index_name="speech_index",
        use_semantic=False,
        load_data=False
    )
# retrieval_service_apple = RetrievalSystemApple(
#     model_name=config.MODEL_NAME_APPLE,
#     milvus_host=config.MILVUS_HOST,
#     milvus_port=config.MILVUS_PORT,
#     collection_name_hnsw=config.COLLECTION_HNSW_APPLE
# )

print("--- Application Started ---")

app = Flask(__name__)
CORS(app)
def get_video_id_from_path(path: str):
    """
    Trích xuất 'Lxx_Vyyy' (hoặc Kxx_Vyyy) ở bất kỳ đâu trong path.
    Ví dụ: 'L21/L21_V001/000000.webp' -> 'L21_V001'
    """
    safe = path.replace("\\", "/")
    # Mở rộng để bắt cả Lxx_Vyyy và Kxx_Vyyy
    m = re.search(r"([LK]\d+_V\d+)", safe)
    return m.group(1) if m else None

@app.route("/search", methods=["GET"])
def search_endpoint():
    try:
        # --- A. Params ---
        query = request.args.get("query")
        query = translator_module.translate(query)
        ocr = request.args.get("ocr")
        audio = request.args.get("colors")
        
        if not query:
            return jsonify({"error": "Thiếu tham số 'query'."}), 400

        k_value = int(request.args.get("k", 500))
        ef_value = k_value*3
        search_params = {"params": {"ef": ef_value}}

        # --- B. Chọn retriever theo mode ---
        mode = request.args.get("mode", "SIGLIP_COLLECTION")  # default = apple


        # --- C. Vector search ---
        if query != 'a':
            initial_results = retrieval_service_siglip_nocap.search(
                query=query,
                k=k_value,
                search_params=search_params
            )
            paths = [res[0] for res in initial_results] 
            clip_scores = [res[1] for res in initial_results]

            reranked_results = []

            if mode == "SIGLIP_COLLECTION":
                # Không có caption => bỏ qua BM25, chỉ dùng normalized clip score
                norm_clip_scores = normalize_scores(clip_scores)
                for i, p in enumerate(paths):
                    reranked_results.append({"path": p, "score": norm_clip_scores[i]})

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
            print(frame_results,"Frame_RESULT_FINAL")
            print(video_results_list,"video_results_list_FINAL")

            
            return jsonify({
                "frame_results": frame_results,
                "video_results": video_results_list
            })
        elif ocr!="a":
            ocr_results = ocr_retriever.search(ocr, top_k=k_value, use_fuzzy=True)
            initial_results = ocr_retriever.display_results(ocr_results, k_value)
            final_paths = [path.replace("\\", "/").split("Keyframes/", 1)[-1].rsplit(".", 1)[0] + ".webp"
 for path in initial_results]
            # 1) frame_results
            frame_results = []
            for path in final_paths:
                frame_results.append({
                    "path": f"/images/Keyframes/{path}",
                    "score": None
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
                        "video_score": None
                    }
                videos_data[video_id]["frames"].append(path)

            # 3) build video_results + all_frames
            video_results_list = []
            for video_id, data in videos_data.items():
                video_frames = []
                for p in data["frames"]:
                    score = None
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
            print(frame_results[:2],"Frame_RESULT_FINAL")
            

            
            return jsonify({
                "frame_results": frame_results,
                "video_results": video_results_list
            })
        elif audio!="a":
            results = audio_retriever.search_with_frames(audio, k=k_value, use_fuzzy=True)
        
        # Get paths
            initial_results = audio_retriever.get_keyframe_paths(results, mode="keyword", top_k=k_value)
            
            final_paths = [path.replace("\\", "/").split("Keyframes/", 1)[-1].rsplit(".", 1)[0] + ".webp"
 for path in initial_results]
            # 1) frame_results
            frame_results = []
            for path in final_paths:
                frame_results.append({
                    "path": f"/images/Keyframes/{path}",
                    "score": None
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
                        "video_score": None
                    }
                videos_data[video_id]["frames"].append(path)

            # 3) build video_results + all_frames
            video_results_list = []
            for video_id, data in videos_data.items():
                video_frames = []
                for p in data["frames"]:
                    score = None
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
            print(frame_results,"Frame_RESULT_FINAL")
            print(video_results_list,"video_results_list_FINAL")

            
            return jsonify({
                "frame_results": frame_results,
                "video_results": video_results_list
            })
        else:
            return jsonify({"frame_results": [], "video_results": []})

        # --- D. Rerank ---
        # NOTE: initial_results format:
        #  - for no-cap collection (siglip_nocap): (path, score)
        #  - for caption collections: (path, score, caption)
        

    except Exception as e:
        print(f"An error occurred in /search endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Đã có lỗi xảy ra trên server."}), 500



@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(config.IMAGE_BASE_PATH, filename)

# ====== 3. Submit kết quả ======
@app.route("/submit-data", methods=["POST"])
def submit_answer():
    # Nhận dữ liệu từ yêu cầu POST
    data = request.get_json()
    
    # Lấy session_id, evaluation_id và body (answer_data)
    session_id = data.get("session_id")
    evaluation_id = data.get("evaluation_id")
    answer_data = data.get("answer_data")

    # Kiểm tra dữ liệu đã nhận
    if not session_id or not evaluation_id or not answer_data:
        return jsonify({"error": "Missing required fields"}), 400

    # Gửi dữ liệu tới API bên ngoài
    url = f"https://eventretrieval.oj.io.vn/api/v2/submit/{evaluation_id}?session={session_id}"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=answer_data, headers=headers)

    # Kiểm tra phản hồi từ API
    if response.status_code == 200:
        print("Nộp bài thành công!")
        return jsonify(response.json()), 200
    else:
        print("Lỗi khi nộp bài:", response.text)
        return jsonify({"error": "Failed to submit"}), response.status_code

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=False)
