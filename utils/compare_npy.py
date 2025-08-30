import numpy as np
import os

# ===== CONFIG =====
features_dir = r"D:\Workplace\AIC_2025\Data\All_Features\OpenCLIP_L14"
images_dir   = r"D:\Workplace\AIC_2025\Data\Keyframes"

levels = [f"L{i}" for i in range(21, 31)]  # L21 -> L30
image_exts = [".webp"]

for level in levels:
    # ==== Load npy features ====
    npy_path = os.path.join(features_dir, f"{level}_features.npy")
    if os.path.exists(npy_path):
        feats = np.load(npy_path)
        num_feats = feats.shape[0]
    else:
        num_feats = 0

    # ==== Count images in subfolders ====
    level_path = os.path.join(images_dir, level)
    num_imgs = 0
    for root, _, files in os.walk(level_path):
        num_imgs += sum(1 for f in files if os.path.splitext(f)[1].lower() in image_exts)

    print(f"{level}: {num_feats} features  |  {num_imgs} images")
