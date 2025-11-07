"""
ELASTICSEARCH OCR RETRIEVAL SYSTEM - with FUZZY SEARCH
Compatible with Elasticsearch 8.11.0

Tính năng:
✅ Keyword Search (BM25)
✅ Fuzzy Search (cho phép gõ sai)
✅ Interactive Search Loop
✅ Incremental Indexing
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

def get_file_hash(filepath: str) -> str:
    """Tính hash của file để phát hiện thay đổi"""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""


def extract_video_and_frame_from_path(image_path: str) -> tuple:
    """
    Extract video name và frame number từ đường dẫn
    
    Example:
    D:\\...\\K11\\K11_V001\\000002.webp
    → video_name: K11_V001
    → frame_idx: 2
    """
    try:
        # Lấy filename: 000002.webp
        filename = os.path.basename(image_path)
        # Lấy frame number: 2
        frame_idx = int(os.path.splitext(filename)[0])
        
        # Lấy video name: K11_V001
        parent_dir = os.path.dirname(image_path)
        video_name = os.path.basename(parent_dir)
        
        return video_name, frame_idx
    except:
        return "unknown", 0


# ========================== MAIN CLASS ==========================

class OCRRetrievalES:
    """
    OCR Retrieval System using Elasticsearch
    
    Features:
    - Keyword search (BM25) with FUZZY option
    - Incremental indexing
    """
    
    def __init__(
        self,
        ocr_json_dir: str,
        host: str = "http://localhost:9200",
        index_name: str = "ocr_index_new",
        load_data: bool = False,
        force_reindex: bool = False,
        index_tracker_file: str = ".indexed_ocr_files.json"
    ):
        """
        Khởi tạo OCR Retrieval System
        
        Args:
            ocr_json_dir: Thư mục chứa các file JSON OCR
            host: Elasticsearch host URL
            index_name: Tên index trong Elasticsearch
            load_data: Có load dữ liệu vào ES không
            force_reindex: True = index lại tất cả
            index_tracker_file: File JSON lưu danh sách file đã index
        """
        self.ocr_json_dir = ocr_json_dir
        self.index_name = index_name
        self.force_reindex = force_reindex
        self.index_tracker_file = index_tracker_file

        print("="*80)
        print("🚀 KHỞI ĐỘNG OCR RETRIEVAL SYSTEM")
        print("="*80)
        
        # Load danh sách file đã index
        self.indexed_files = self._load_indexed_files()
        
        # Kết nối Elasticsearch
        self._connect_elasticsearch(host)
        

        
        # Tạo index
        self._setup_index()
        
        # Index dữ liệu
        if load_data:
            self._index_data()

    def _load_indexed_files(self) -> Dict[str, str]:
        """Load danh sách file đã index từ file JSON"""
        if self.force_reindex:
            print("\n⚠️  Force reindex enabled - sẽ index lại tất cả file")
            return {}
        
        if os.path.exists(self.index_tracker_file):
            try:
                with open(self.index_tracker_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"\n📋 Đã load thông tin {len(data)} file đã index")
                return data
            except Exception as e:
                print(f"\n⚠️  Không thể đọc {self.index_tracker_file}: {e}")
                return {}
        else:
            print(f"\n📋 File tracker chưa tồn tại - sẽ tạo mới")
            return {}

    def _save_indexed_files(self):
        """Lưu danh sách file đã index vào file JSON"""
        try:
            with open(self.index_tracker_file, 'w', encoding='utf-8') as f:
                json.dump(self.indexed_files, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Đã lưu thông tin {len(self.indexed_files)} file")
        except Exception as e:
            print(f"\n⚠️  Không thể lưu tracker: {e}")

    def _should_index_file(self, filepath: str) -> bool:
        """Kiểm tra xem file có cần index không"""
        if self.force_reindex:
            return True
        
        current_hash = get_file_hash(filepath)
        
        if filepath in self.indexed_files:
            stored_hash = self.indexed_files[filepath]
            if stored_hash == current_hash:
                return False
        
        return True

    def _connect_elasticsearch(self, host: str):
        """Kết nối tới Elasticsearch"""
        print(f"\n🔌 Đang kết nối tới {host}...")
        
        try:
            from elasticsearch import __version__ as es_version
            print(f"   Phiên bản client: {es_version}")
            
            self.es = Elasticsearch(
                hosts=[host],
                verify_certs=False,
                ssl_show_warn=False,
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            info = self.es.info()
            print(f"✅ Kết nối thành công!")
            print(f"   - Cluster: {info['cluster_name']}")
            print(f"   - Version: {info['version']['number']}")
            
        except Exception as e:
            print(f"\n❌ LỖI KẾT NỐI: {e}")
            raise ConnectionError("Không thể kết nối tới Elasticsearch!")

    def _setup_index(self):
        """Tạo index nếu chưa tồn tại"""
        print(f"\n🔧 Kiểm tra index '{self.index_name}'...")
        
        try:
            if self.es.indices.exists(index=self.index_name):
                print(f"ℹ️  Index đã tồn tại")
                return
            
            print(f"🔨 Tạo index mới...")
            mapping = {
                "mappings": {
                    "properties": {
                        "text": {"type": "text"},
                        "image_path": {"type": "keyword"},
                        "filename": {"type": "keyword"},
                        "video_name": {"type": "keyword"},
                        "frame_idx": {"type": "integer"},
                        "source_file": {"type": "keyword"}
                        }
                    }
                }
            
            self.es.indices.create(index=self.index_name, body=mapping)
            print("✅ Index đã được tạo!")
            
        except Exception as e:
            print(f"⚠️  Lỗi khi tạo index: {e}")
            raise

    def _index_data(self):
        """Đọc và index dữ liệu từ các file JSON OCR"""
        print("\n" + "="*80)
        print("📂 BẮT ĐẦU INDEX DỮ LIỆU OCR (INCREMENTAL)")
        print("="*80)
        print(f"Thư mục: {self.ocr_json_dir}\n")
        
        # Đếm số file
        all_files = []
        for root, _, files in os.walk(self.ocr_json_dir):
            for file in files:
                if file.endswith(".json"):
                    all_files.append(os.path.join(root, file))
        
        print(f"📊 Tổng số file JSON: {len(all_files)}")
        print(f"📋 Số file đã index trước đó: {len(self.indexed_files)}")
        
        # Lọc file cần index
        files_to_index = [f for f in all_files if self._should_index_file(f)]
        files_skipped = len(all_files) - len(files_to_index)
        
        print(f"🆕 File cần index: {len(files_to_index)}")
        print(f"⏭️  File bỏ qua (đã index): {files_skipped}")
        
        if len(files_to_index) == 0:
            print("\n✅ Không có file mới - Bỏ qua indexing")
            return
        
        print()
        
        count = 0
        indexed_count = 0
        
        for full_path in files_to_index:
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                file_display = os.path.basename(full_path)
                print(f"📄 {file_display} ({len(data)} entries)")
                
                # Index từng entry
                for image_path, ocr_data in tqdm(data.items(), desc=f"  Indexing", leave=False):
                    # ocr_data format: ["filename.webp", "text content"]
                    if not isinstance(ocr_data, list) or len(ocr_data) < 2:
                        continue
                    
                    filename = ocr_data[0]
                    text = ocr_data[1].strip()
                    
                    if not text:
                        continue
                    
                    # Extract video name và frame number
                    video_name, frame_idx = extract_video_and_frame_from_path(image_path)
                    
                    doc = {
                        "text": text,
                        "image_path": image_path,
                        "filename": filename,
                        "video_name": video_name,
                        "frame_idx": frame_idx,
                        "source_file": full_path
                    }

                self.es.index(index=self.index_name, document=doc)
                # Cập nhật hash của file vào tracker
                self.indexed_files[full_path] = get_file_hash(full_path)
                indexed_count += 1
                
                print(f"   ✅ Đã index xong\n")
                
            except Exception as e:
                print(f"   ⚠️  Lỗi: {e}\n")
        
        # Lưu danh sách file đã index
        self._save_indexed_files()

    def search(self, query: str, top_k, use_fuzzy: bool = False) -> Dict:
        results = {}

        # 1. Keyword Search (BM25) với Fuzzy option
        if use_fuzzy:
            keyword_query = {
                "size": top_k,
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
                "size": top_k,
                "query": {"match": {"text": query}}
            }
        
        resp = self.es.search(index=self.index_name, body=keyword_query)
        results["keyword"] = [hit["_source"] for hit in resp["hits"]["hits"]]

        return results

    def display_results(self, results: Dict, top_k):
        mode_results = results.get("keyword", [])  # ✅ Lấy ra ngoài loop
    
        if not mode_results:
            print("❌ Không tìm thấy kết quả")
            return []  # ✅ Return empty list
    
            # Giới hạn số kết quả nếu cần
        display_list = mode_results[:top_k] if top_k else mode_results
    
    # Return list paths
        paths = [r.get('image_path', 'N/A') for r in display_list]
        return paths

    def reset_index_tracker(self):
        """Xóa file tracker - dùng khi muốn index lại từ đầu"""
        if os.path.exists(self.index_tracker_file):
            os.remove(self.index_tracker_file)
            print(f"🗑️  Đã xóa {self.index_tracker_file}")
            self.indexed_files = {}
        else:
            print(f"ℹ️  File {self.index_tracker_file} không tồn tại")


# ========================== INTERACTIVE SEARCH ==========================
def interactive_ocr_search(query, top_k, OCR_JSON_DIR, index_name,retrieval):
    retrieval = retrieval
    
    # ✅ BỎ while True, chỉ search 1 lần
    try:
        results = retrieval.search(query, top_k=top_k, use_fuzzy=True)
        return retrieval.display_results(results, top_k)
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")



# ========================== MAIN PROGRAM ==========================

if __name__ == "__main__":
    # Cấu hình đường dẫn
    OCR_JSON_DIR = r"D:\Workplace\OCR\Output"  # ⚠️ THAY ĐỔI ĐƯỜNG DẪN NÀY
    
    # ============ CHẾ ĐỘ 1: INDEX DỮ LIỆU ============
    retrieval = OCRRetrievalES(
        ocr_json_dir=OCR_JSON_DIR,
        host="http://localhost:9200",
        index_name="ocr_index_new",
        load_data=True,  # True = index dữ liệu
        force_reindex=True
    )
    
    # # ============ CHẾ ĐỘ 2: CHỈ TÌM KIẾM ============
    
    # print (interactive_ocr_search("trả nợ", 500, OCR_JSON_DIR, "ocr_index_main"))