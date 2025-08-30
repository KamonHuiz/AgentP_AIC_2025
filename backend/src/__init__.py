"""
File này biến thư mục `src` thành một Python package.

Chúng ta import class RetrievalSystem ở đây để có thể gọi trực tiếp
từ package `src` thay vì phải chỉ rõ tên file.

Thay vì viết: from src.retrieval_system import RetrievalSystem
Ta có thể viết: from src import RetrievalSystem
"""
from .retrieval_system import RetrievalSystem,RetrievalSystemApple
