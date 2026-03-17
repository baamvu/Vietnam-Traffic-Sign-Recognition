# Vietnam Traffic Sign Recognition

Ứng dụng nhận diện biển báo giao thông Việt Nam sử dụng **YOLOv5** và **Streamlit**, hỗ trợ **100 loại biển báo** theo tiêu chuẩn QCVN 41:2019/BGTVT.

## Demo

Ứng dụng hỗ trợ 3 chế độ nhận diện:

| Chế độ | Mô tả |
|--------|-------|
| **Ảnh** | Upload ảnh (JPG, PNG, BMP, WebP) để nhận diện |
| **Video** | Upload video (MP4, AVI, MOV...) để xử lý từng frame |
| **Webcam** | Chụp ảnh trực tiếp từ webcam để nhận diện |

## Tính năng

- Nhận diện **100 loại biển báo** giao thông Việt Nam
- Hiển thị bounding box với mã màu theo nhóm biển báo:
  - **Đỏ** — Biển cấm (P)
  - **Cam** — Hết cấm (DP)
  - **Xanh dương** — Biển hiệu lệnh (R)
  - **Xanh lá** — Biển chỉ dẫn (S)
  - **Vàng** — Biển cảnh báo (W)
  - **Xám** — Đèn giao thông
- Bảng chi tiết kết quả (mã biển, ý nghĩa, độ tin cậy, vị trí)
- Tải ảnh/video kết quả về máy
- Tùy chỉnh ngưỡng confidence

## Các nhóm biển báo được hỗ trợ

| Nhóm | Số lượng | Ví dụ |
|------|----------|-------|
| Biển cấm (P) | 48 | P.102 Cấm đi ngược chiều, P.127 Tốc độ tối đa |
| Biển hiệu lệnh (R) | 15 | R.303 Vòng xuyến, R.407a Đường một chiều |
| Biển cảnh báo (W) | 32 | W.224 Người đi bộ, W.225 Trẻ em |
| Biển chỉ dẫn (S) | 1 | S.509a Biển chỉ dẫn |
| Hết cấm (DP) | 1 | DP.135 Hết cấm |
| Đèn giao thông | 3 | Đèn đỏ, đèn vàng, đèn xanh |

## Cài đặt

### Yêu cầu

- Python 3.8+
- FFmpeg (tùy chọn, để xuất video H.264)

### Các bước

```bash
# 1. Clone repository
git clone https://github.com/baamvu/Vietnam-Traffic-Sign-Recognition.git
cd Vietnam-Traffic-Sign-Recognition

# 2. Cài đặt thư viện
pip install -r requirements.txt

# 3. Chạy ứng dụng
streamlit run app.py
```

Ứng dụng sẽ mở tại `http://localhost:8501`.

## Cấu trúc project

```
Vietnam-Traffic-Sign-Recognition/
├── app.py              # Ứng dụng Streamlit chính
├── best.pt             # Model YOLOv5 đã train
├── requirements.txt    # Thư viện Python
├── .gitignore
└── README.md
```

## Hướng dẫn train model

Nếu muốn train lại model với dữ liệu riêng:

1. Chuẩn bị dataset trên [Roboflow](https://roboflow.com) (format **YOLOv5 PyTorch**)
2. Train trên Google Colab:

```python
# Clone YOLOv5
!git clone https://github.com/ultralytics/yolov5
%cd yolov5
!pip install -r requirements.txt

# Tải dataset từ Roboflow
!pip install roboflow
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("YOUR_WORKSPACE").project("YOUR_PROJECT")
dataset = project.version(1).download("yolov5")

# Train
!python train.py --img 640 --batch 16 --epochs 100 \
    --data {dataset.location}/data.yaml \
    --weights yolov5s.pt --name traffic_sign
```

3. Copy `runs/train/traffic_sign/weights/best.pt` vào thư mục project

## Công nghệ sử dụng

- **YOLOv5** — Object detection
- **Streamlit** — Web UI
- **OpenCV** — Xử lý ảnh/video
- **PyTorch** — Deep learning framework

## License

MIT
