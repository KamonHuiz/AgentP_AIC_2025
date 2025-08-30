import os, json
from natsort import natsorted
import numpy as np
# Cấu hình
base_dir = r"D:\Workplace\AIC_2025\Data\Keyframes"
l_folder = "L24"
feature_dim = 1024

# File feature npy
npy_file = fr"D:\Workplace\AIC_2025\Data\All_Features\Apple_Feature\L24.npy"
features = np.load(npy_file)
features = features.reshape(-1, feature_dim)

# Hàm convert path cho đồng nhất
def convert_path(original_path):
    idx = original_path.replace("\\", "/").find("Keyframes")
    if idx != -1:
        return "D:/Workplace/AIC_2025/Data/" + original_path[idx:].replace("\\", "/")
    else:
        return original_path

# Lấy danh sách ảnh trong L22
l_path = os.path.join(base_dir, l_folder)
image_paths = []
for v_folder in natsorted(os.listdir(l_path)):
    v_path = os.path.join(l_path, v_folder)
    if not os.path.isdir(v_path):
        continue
    for img_file in natsorted(os.listdir(v_path)):
        if img_file.lower().endswith((".jpg", ".webp")):
            image_paths.append(os.path.join(v_path, img_file))

# Tạo mapping JSON
mapping = {convert_path(p): i for i, p in enumerate(image_paths)}

# Lưu mapping ra file
json_file = fr"D:\Workplace\AIC_2025\Data\All_Features\Apple_Feature\{l_folder}_Apple_mapping.json"
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(mapping, f, indent=2)

# Kiểm tra số lượng
print("Số ảnh trong thư mục:", len(image_paths))
print("Số feature trong npy:", features.shape[0])
print("Có khớp không? ->", len(image_paths) == features.shape[0])
print(f"✅ Mapping JSON đã lưu: {json_file}")
