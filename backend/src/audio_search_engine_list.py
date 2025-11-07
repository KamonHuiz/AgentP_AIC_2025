"""
ELASTICSEARCH SPEECH RETRIEVAL SYSTEM - SIMPLE VERSION
Compatible with Elasticsearch 8.11.0

Tính năng:
✅ Keyword Search (BM25)
✅ Semantic Search (Dense Vector)
✅ Fuzzy Search
✅ Return list keyframe paths (giống OCR search)
"""

import os
import json
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from typing import List, Dict
import warnings
import hashlib
warnings.filterwarnings('ignore')


# ========================== HELPER FUNCTIONS ==========================
def list_keyframes_in_range(entry: Dict, base_keyframe_dir: str) -> List[str]:
    """Lấy danh sách frame thực tế trong thư mục Keyframes"""
    json_file = os.path.basename(entry["file"])
    video_name = os.path.splitext(json_file)[0]
    k_folder = video_name.split('_')[0]
    keyframe_folder = os.path.join(base_keyframe_dir, k_folder, video_name)
    
    start_f, end_f = entry["start_frame"], entry["end_frame"]
    frame_paths = []

    if os.path.exists(keyframe_folder):
        for fname in sorted(os.listdir(keyframe_folder)):
            if fname.endswith((".webp", ".jpg", ".png")):
                try:
                    frame_num = int(os.path.splitext(fname)[0])
                    if start_f <= frame_num <= end_f:
                        frame_paths.append(os.path.join(keyframe_folder, fname))
                except ValueError:
                    continue
    
    return frame_paths


def get_file_hash(filepath: str) -> str:
    """Tính hash của file"""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""


# ========================== MAIN CLASS ==========================
class SpeechRetrievalES:
    """Speech Retrieval System using Elasticsearch"""
    
    def __init__(
        self,
        context_json_dir: str,
        base_keyframe_dir: str,
        host: str = "http://localhost:9200",
        index_name: str = "speech_index",
        semantic_model: str = "sentence-transformers/stsb-xlm-r-multilingual",
        use_semantic: bool = True,
        load_data: bool = True,
        force_reindex: bool = False,
        index_tracker_file: str = ".indexed_files.json"
    ):
        self.context_json_dir = context_json_dir
        self.base_keyframe_dir = base_keyframe_dir
        self.index_name = index_name
        self.use_semantic = use_semantic
        self.force_reindex = force_reindex
        self.index_tracker_file = index_tracker_file

        print("="*80)
        print("🚀 KHỞI ĐỘNG SPEECH RETRIEVAL SYSTEM")
        print("="*80)
        
        self.indexed_files = self._load_indexed_files()
        self._connect_elasticsearch(host)
        
        if use_semantic:
            self._load_semantic_model(semantic_model)
        
        self._setup_index()
        
        if load_data:
            self._index_data()

    def _load_indexed_files(self) -> Dict[str, str]:
        if self.force_reindex:
            return {}
        if os.path.exists(self.index_tracker_file):
            try:
                with open(self.index_tracker_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_indexed_files(self):
        try:
            with open(self.index_tracker_file, 'w', encoding='utf-8') as f:
                json.dump(self.indexed_files, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  Lỗi lưu tracker: {e}")

    def _should_index_file(self, filepath: str) -> bool:
        if self.force_reindex:
            return True
        current_hash = get_file_hash(filepath)
        if filepath in self.indexed_files:
            if self.indexed_files[filepath] == current_hash:
                return False
        return True

    def _connect_elasticsearch(self, host: str):
        print(f"\n🔌 Đang kết nối tới {host}...")
        self.es = Elasticsearch(
            hosts=[host],
            verify_certs=False,
            ssl_show_warn=False,
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        info = self.es.info()
        print(f"✅ Kết nối thành công! Version: {info['version']['number']}")

    def _load_semantic_model(self, model_name: str):
        print(f"\n📥 Đang tải model...")
        self.model = SentenceTransformer(model_name)
        print("✅ Model sẵn sàng!")

    def _setup_index(self):
        print(f"\n🔧 Kiểm tra index '{self.index_name}'...")
        if self.es.indices.exists(index=self.index_name):
            print(f"ℹ️  Index đã tồn tại")
            return
        
        mapping = {
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
                    "start_frame": {"type": "integer"},
                    "end_frame": {"type": "integer"},
                    "start_sec": {"type": "float"},
                    "end_sec": {"type": "float"},
                    "file": {"type": "keyword"},
                    "video_name": {"type": "keyword"},
                    "L": {"type": "integer"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 768,
                        "index": True,
                        "similarity": "cosine"
                    }
                }
            }
        }
        
        self.es.indices.create(index=self.index_name, body=mapping)
        print("✅ Index đã tạo!")

    def _index_data(self):
        print("\n📂 BẮT ĐẦU INDEX DỮ LIỆU")
        
        all_files = []
        for root, _, files in os.walk(self.context_json_dir):
            for file in files:
                if file.endswith(".json"):
                    all_files.append(os.path.join(root, file))
        
        files_to_index = [f for f in all_files if self._should_index_file(f)]
        
        if len(files_to_index) == 0:
            print("✅ Không có file mới")
            return
        
        count = 0
        for full_path in files_to_index:
            video_name = os.path.splitext(os.path.basename(full_path))[0]
            
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for idx, item in enumerate(tqdm(data, desc=f"Indexing", leave=False)):
                text = item.get("text", "").strip()
                if not text:
                    continue
                
                doc = {
                    "text": text,
                    "start_frame": item.get("start_frame"),
                    "end_frame": item.get("end_frame"),
                    "start_sec": item.get("start_sec"),
                    "end_sec": item.get("end_sec"),
                    "file": full_path,
                    "video_name": video_name,
                    "L": idx,
                }

                if self.use_semantic:
                    doc["embedding"] = self.model.encode(text).tolist()

                self.es.index(index=self.index_name, document=doc)
                count += 1
            
            self.indexed_files[full_path] = get_file_hash(full_path)
        
        self._save_indexed_files()
        print(f"🎉 Đã index {count:,} documents!")

    def search(self, query: str, k: int = 3, use_fuzzy: bool = False) -> Dict:
        """Tìm kiếm keyword và semantic"""
        results = {}

        # Keyword Search
        if use_fuzzy:
            keyword_query = {
                "size": k,
                "query": {
                    "match": {
                        "text": {
                            "query": query,
                            "fuzziness": "AUTO",
                            "prefix_length": 1,
                            "max_expansions": 50
                        }
                    }
                }
            }
        else:
            keyword_query = {
                "size": k,
                "query": {"match": {"text": query}}
            }
        
        resp = self.es.search(index=self.index_name, body=keyword_query)
        results["keyword"] = [hit["_source"] for hit in resp["hits"]["hits"]]

        # Semantic Search
        if self.use_semantic:
            query_vec = self.model.encode(query).tolist()
            
            semantic_query = {
                "size": k,
                "knn": {
                    "field": "embedding",
                    "query_vector": query_vec,
                    "k": k,
                    "num_candidates": 100
                }
            }
            
            try:
                resp = self.es.search(index=self.index_name, **semantic_query)
                results["semantic"] = [hit["_source"] for hit in resp["hits"]["hits"]]
            except Exception as e:
                print(f"⚠️  Lỗi semantic: {e}")
                results["semantic"] = []

        return results

    def search_with_frames(self, query: str, k: int = 3, use_fuzzy: bool = False) -> Dict:
        """Search và lấy keyframes"""
        results = self.search(query, k, use_fuzzy)
        output = {}

        for mode in ["semantic", "keyword"]:
            output[mode] = []
            for r in results.get(mode, []):
                frames = list_keyframes_in_range(r, self.base_keyframe_dir)
                r["frames"] = frames
                r["num_frames"] = len(frames)
                output[mode].append(r)
        
        return output

    def get_keyframe_paths(self, results: Dict, mode: str = "semantic", top_k: int = None) -> list:
        """
        Lấy danh sách đường dẫn keyframes
        
        Args:
            results: Kết quả từ search_with_frames()
            mode: "semantic" hoặc "keyword"
            top_k: Giới hạn số kết quả
        
        Returns:
            list: Danh sách đường dẫn keyframes
        """
        mode_results = results.get(mode, [])
        
        if not mode_results:
            return []
        
        # Giới hạn
        display_list = mode_results[:top_k] if top_k else mode_results
        
        # Lấy tất cả keyframes
        all_paths = []
        for r in display_list:
            frames = r.get('frames', [])
            all_paths.extend(frames)
        
        return all_paths


# ========================== SEARCH FUNCTION ==========================

def audio_search(query: str, top_k: int, audio_dir: str, keyframe_dir: str, 
                 index_name: str = "speech_index", use_fuzzy: bool = True, use_semantic: bool = False,
                 mode: str = "semantic") -> list:
    """
    Search audio transcripts và trả về list keyframe paths
    
    Args:
        query: Query string
        top_k: Số kết quả trả về
        audio_dir: Thư mục chứa JSON transcripts
        keyframe_dir: Thư mục chứa keyframes
        index_name: Tên index
        use_fuzzy: Bật fuzzy search
        mode: "semantic" hoặc "keyword"
    
    Returns:
        list: Danh sách đường dẫn keyframes
    """
    retrieval = SpeechRetrievalES(
        context_json_dir=audio_dir,
        base_keyframe_dir=keyframe_dir,
        host="http://localhost:9200",
        index_name=index_name,
        use_semantic=False,
        load_data=False
    )
    
    try:
        # Search
        results = retrieval.search_with_frames(query, k=top_k, use_fuzzy=use_fuzzy)
        
        # Get paths
        paths = retrieval.get_keyframe_paths(results, mode=mode, top_k=top_k)
        
        return paths
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return []


# ========================== MAIN PROGRAM ==========================

if __name__ == "__main__":
    # Cấu hình
    AUDIO_DIR = r"D:\Workplace\AIC_2025\Data\AUDIO_RECOGNIZATION"
    KEYFRAME_DIR = r"D:\Workplace\AIC_2025\Data\Keyframes"
    
    # ============ INDEX (nếu cần) ============
    retrieval = SpeechRetrievalES(
        context_json_dir=AUDIO_DIR,
        base_keyframe_dir=KEYFRAME_DIR,
        host="http://localhost:9200",
        index_name="speech_index",
        use_semantic=False,
        load_data=True,
        force_reindex=False
    )
    
    # # ============ SEARCH ============
    # print(audio_search(
    #     query="xe ô tô",
    #     top_k=500,
    #     audio_dir=AUDIO_DIR,
    #     keyframe_dir=KEYFRAME_DIR,
    #     index_name="speech_index",
    #     use_fuzzy=True,
    #     mode="keyword",
    #     use_semantic=False
    # ))