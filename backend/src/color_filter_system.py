import os
import h5py
import numpy as np
from tqdm import tqdm
from skimage.color import deltaE_ciede2000
from matplotlib.colors import to_rgba
from typing import List

class ColorFilterSystem:
    """
    Class đóng gói hệ thống lọc ảnh dựa trên màu sắc.
    """
    def __init__(self, hdf5_dir: str):
        """
        Khởi tạo hệ thống, tải toàn bộ dữ liệu màu từ các file HDF5.
        """
        print("Initializing Color Filter System...")
        all_paths, all_lab = [], []

        for file_name in sorted(os.listdir(hdf5_dir)):
            if file_name.endswith('.h5') or file_name.endswith('.hdf5'):
                file_path = os.path.join(hdf5_dir, file_name)
                print(f"🎨 Reading color data from: {file_path}")
                with h5py.File(file_path, 'r') as f:
                    paths = f['paths'][:]
                    lab_data = f['lab'][:]
                    all_paths.append(paths)
                    all_lab.append(lab_data)
        
        # Nối dữ liệu từ các file
        all_paths = np.concatenate(all_paths)
        all_paths = [p.decode() if isinstance(p, bytes) else str(p) for p in all_paths]
        self.all_lab = np.concatenate(all_lab)
        
        # Tạo một map để tra cứu index từ path, giúp tăng tốc độ
        self.path_to_index = {path: i for i, path in enumerate(all_paths)}
        print(f"✅ Color data for {len(all_paths)} images loaded.")

    def _name_to_rgb(self, color_name: str) -> List[int]:
        rgba = to_rgba(color_name.replace(" ", "").lower())
        return [int(c * 255) for c in rgba[:3]]

    def _rgb_to_lab(self, rgb: List[int]) -> List[float]:
        rgb = np.array(rgb, dtype=np.float32) / 255.0
        def pivot_rgb(c): return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
        r, g, b = [pivot_rgb(c) for c in rgb]
        r, g, b = r * 100, g * 100, b * 100
        X = r * 0.4124 + g * 0.3576 + b * 0.1805
        Y = r * 0.2126 + g * 0.7152 + b * 0.0722
        Z = r * 0.0193 + g * 0.1192 + b * 0.9505
        X, Y, Z = X / 95.047, Y / 100.000, Z / 108.883
        def pivot_xyz(c): return c ** (1/3) if c > 0.008856 else (7.787 * c) + (16 / 116)
        X, Y, Z = pivot_xyz(X), pivot_xyz(Y), pivot_xyz(Z)
        L = (116 * Y) - 16
        a = 500 * (X - Y)
        b = 200 * (Y - Z)
        return [L, a, b]

    def filter_by_colors(self, image_paths: List[str], color_names: List[str]) -> List[str]:
        """
        Lọc một danh sách các đường dẫn ảnh dựa trên danh sách màu sắc.
        """
        if not color_names or not image_paths:
            return image_paths

        # Chuyển đổi màu người dùng nhập sang không gian LAB
        user_lab_colors = np.array([self._rgb_to_lab(self._name_to_rgb(c)) for c in color_names])

        # Tính toán DeltaE cho mỗi ảnh trong danh sách đầu vào
        deltaE_list = []
        for img_path in image_paths:
            if img_path not in self.path_to_index:
                deltaE_list.append(np.inf) # Gán giá trị vô cùng nếu không có dữ liệu màu
                continue
            
            idx = self.path_to_index[img_path]
            img_labs = self.all_lab[idx]

            deltas = []
            for user_lab in user_lab_colors:
                # Tính khoảng cách màu giữa mỗi màu của ảnh và màu của người dùng
                img_deltas = deltaE_ciede2000(img_labs, np.tile(user_lab, (img_labs.shape[0], 1)))
                deltas.append(img_deltas.min()) # Lấy khoảng cách nhỏ nhất
            
            avg_delta = np.mean(deltas)
            deltaE_list.append(avg_delta)
        
        deltaE_array = np.array(deltaE_list)
        
        # Lọc kết quả: chỉ giữ lại các ảnh có DeltaE nhỏ hơn Q3
        valid_deltas = deltaE_array[deltaE_array != np.inf]
        if len(valid_deltas) == 0:
            return [] # Không có ảnh nào hợp lệ để lọc

        Q3 = np.percentile(valid_deltas, 55)
        
        # Trả về danh sách các path đã được lọc
        filtered_paths = [p for p, d in zip(image_paths, deltaE_array) if d < Q3]
        return filtered_paths