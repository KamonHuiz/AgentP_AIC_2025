import torch
import open_clip
import torch.nn.functional as F
from open_clip import create_model_from_pretrained, get_tokenizer
from pymilvus import Collection, connections
from typing import List, Tuple

class RetrievalSystem:
    """
    Class này đóng gói hệ thống tìm kiếm, có khả năng sử dụng nhiều collection Milvus.
    """
    def __init__(self, model_name: str, pretrained: str, milvus_host: str, milvus_port: str, 
                 collection_name_hnsw: str):
        """
        Khởi tạo hệ thống.
        - Tải model CLIP.
        - Kết nối tới Milvus và tải CẢ HAI collection HNSW và IVF_FLAT.
        """
        print("Initializing Flexible Retrieval System...")
        
        # 1. Tải model CLIP (chỉ tải 1 lần, tiết kiệm tài nguyên)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"✅ Using device: {self.device}")
        self.model, _, _ = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained, device=self.device
        )
        self.tokenizer = open_clip.get_tokenizer(model_name)
        self.model.eval()
        print("✅ CLIP Model loaded.")

        # 2. Kết nối tới Milvus và tải cả hai collection
        try:
            print(f"Connecting to Milvus at {milvus_host}:{milvus_port}...")
            connections.connect("default", host=milvus_host, port=milvus_port)
            print("✅ Connected to Milvus.")
            
            print(f"Loading HNSW collection: '{collection_name_hnsw}'...")
            self.collection_hnsw = Collection(collection_name_hnsw)
            self.collection_hnsw.load()
        
            print("Loaded Collection")

        except Exception as e:
            print(f"❌ Failed to connect to Milvus or load collections: {e}")
            raise

    @torch.no_grad()
    def _encode_text(self, query: str) -> List[float]:
        """Mã hóa một câu truy vấn văn bản thành vector."""
        tokens = self.tokenizer([query]).to(self.device)
        text_features = self.model.encode_text(tokens)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        return text_features[0].cpu().tolist()

    def search(self, query: str, k: int, search_params: dict) -> List[Tuple[str, float, str]]:
        """
        Thực hiện tìm kiếm trên collection được chỉ định.
        
        Args:
            query (str): Câu truy vấn.
            k (int): Số lượng kết quả.
            index_type (str): Loại index cần dùng ('hnsw' hoặc 'ivf').
            search_params (dict): Tham số tìm kiếm cho Milvus.
        """
        # 1. Mã hóa query
        query_vector = self._encode_text(query)


        # 3. Tìm kiếm trên collection đã chọn
        results = self.collection_hnsw.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,  # {"metric_type": "IP", "params": {"ef": 800}}
            limit=k,
            output_fields=["path", "caption"]
        )

        hits = results[0]
        formatted_results = []
        for hit in hits:
            path = hit.entity.get('path')
            caption = hit.entity.get('caption')
            score = hit.score   # Milvus trả thẳng về similarity
            formatted_results.append((path, score, caption))
        return formatted_results
    
class RetrievalSystemApple:
    """
    RetrievalSystemApple: chuyên dùng cho model Apple CLIP.
    - Load model từ HuggingFace Hub.
    - Kết nối Milvus và search.
    """
    def __init__(self, model_name: str, milvus_host: str, milvus_port: str, collection_name_hnsw: str):
        print("Initializing Apple Retrieval System...")

        # 1. Device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"✅ Using device: {self.device}")

        # 2. Load Apple model
        self.model, self.preprocess = create_model_from_pretrained(model_name)
        self.tokenizer = get_tokenizer("ViT-H-14")
        self.model = self.model.to(self.device)
        self.model.eval()
        print("✅ Apple CLIP model loaded.")

        # 3. Kết nối Milvus
        try:
            print(f"Connecting to Milvus at {milvus_host}:{milvus_port}...")
            connections.connect("default", host=milvus_host, port=milvus_port)
            print("✅ Connected to Milvus.")

            print(f"Loading HNSW collection: '{collection_name_hnsw}'...")
            self.collection_hnsw = Collection(collection_name_hnsw)
            self.collection_hnsw.load()

            print("✅ Collection loaded.")

        except Exception as e:
            print(f"❌ Failed to connect to Milvus or load collection: {e}")
            raise

    @torch.no_grad()
    def _encode_text(self, query: str):
        """Mã hóa query text bằng Apple CLIP model."""
        tokens = self.tokenizer([query], context_length=self.model.context_length).to(self.device)
        text_features = self.model.encode_text(tokens)
        text_features = F.normalize(text_features, dim=-1)
        return text_features[0].cpu().tolist()

    def search(self, query: str, k: int, search_params: dict):
        """
        Search ảnh trong collection Apple.
        Args:
            query (str): câu truy vấn
            k (int): số lượng kết quả
            search_params (dict): tham số search cho Milvus
        """
        query_vector = self._encode_text(query)

        results = self.collection_hnsw.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=k,
            output_fields=["path", "caption"]
        )

        hits = results[0]
        formatted_results = []
        for hit in hits:
            path = hit.entity.get("path")
            caption = hit.entity.get("caption")
            score = hit.score
            formatted_results.append((path, score, caption))
        return formatted_results
    
class RetrievalSystemSiglipNoCap:
    """
    Retrieval System cho SigLip nhưng KHÔNG có caption.
    """
    def __init__(self, model_name: str, pretrained: str, milvus_host: str, milvus_port: str,
                 collection_name_hnsw: str):
        print("Initializing SigLip Retrieval System (no caption)...")

        # 1. Load model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"✅ Using device: {self.device}")
        self.model, _, _ = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained, device=self.device
        )
        self.tokenizer = open_clip.get_tokenizer(model_name)
        self.model.eval()
        print("✅ SigLip model loaded.")

        # 2. Connect Milvus + load collection
        try:
            print(f"Connecting to Milvus at {milvus_host}:{milvus_port}...")
            connections.connect("default", host=milvus_host, port=milvus_port)
            print("✅ Connected to Milvus.")

            print(f"Loading HNSW collection: '{collection_name_hnsw}'...")
            self.collection_hnsw = Collection(collection_name_hnsw)
            self.collection_hnsw.load()

            print("✅ Collection loaded.")
        except Exception as e:
            print(f"❌ Failed to connect/load collection: {e}")
            raise

    @torch.no_grad()
    def _encode_text(self, query: str) -> List[float]:
        """Encode query text thành vector."""
        tokens = self.tokenizer([query]).to(self.device)
        text_features = self.model.encode_text(tokens)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        return text_features[0].cpu().tolist()

    def search(self, query: str, k: int, search_params: dict) -> List[Tuple[str, float]]:
        """
        Tìm kiếm KHÔNG có caption.
        Trả về list (path, score).
        """
        query_vector = self._encode_text(query)

        results = self.collection_hnsw.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=k,
            output_fields=["path"]  # ❌ bỏ caption
        )

        hits = results[0]
        formatted_results = []
        for hit in hits:
            path = hit.entity.get("path")
            #base_path = "D:/Workplace/AIC_2025/Data/Keyframes"
            #path = path.replace("D:/Workplace/AIC_2025/Data/Keyframes/", "")
            score = hit.score
            formatted_results.append((path, score))
        return formatted_results
