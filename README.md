# video_retrieval_aic_2025

# AIC_System

Agent P Baseline

## Cài đặt môi trường

```bash
# 1. Cài Python 3.11.9 (link tải: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe)

# 2. Clone project vào ổ D:\Workplace\Test_Baseline
git clone https://github.com/KamonHuiz/AIC_Baseline.git

# 3. Tạo và kích hoạt môi trường ảo
Tạo môi trường ảo nha
.venv\Scripts\activate

# 4. Cài đặt thư viện
pip install -r requirements.txt

# CẤU HÌNH GIT LẦN ĐẦU
git config --global user.email "kamonwalter72@gmail.com"
git config --global user.name "KamonHuiz"

# LUỒNG LÀM VIỆC CHUẨN
git pull                    # Luôn kéo code mới về
git add .                   # Thêm tất cả file thay đổi
git commit -m "Nội dung báo cáo"
git push                    # Đẩy code lên

# KHÁC
git restore .               # Hủy mọi thay đổi local (nếu cần)
```

## Tải data

1. Vào folders rồi tải
   https://drive.google.com/file/d/1RKP9qUZcxYN17NZfpvt3sof2GYpvmXr2/view?usp=sharing

## Run system

cd vô backend
Terminal 1
python app.py

cd vô frontend
Terminal 2
python -m http.server 8000

truy cập đường dẫn sau
http://localhost:8000/index.html
