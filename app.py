import streamlit as st
import torch
import cv2
import numpy as np
import tempfile
import os
import pathlib
from PIL import Image

if os.name == "nt":
    pathlib.PosixPath = pathlib.WindowsPath

SIGN_INFO = {
    # ── Hết cấm (DP) ────────────────────────────────────────────
    "DP.135": "Hết cấm",
    # ── Biển cấm (P) ────────────────────────────────────────────
    "P.101": "Đường cấm",
    "P.102": "Cấm đi ngược chiều",
    "P.103a": "Cấm ô tô",
    "P.103b": "Cấm ô tô rẽ trái",
    "P.103c": "Cấm ô tô rẽ phải",
    "P.103d": "Cấm taxi",
    "P.104": "Cấm mô tô",
    "P.105": "Cấm xe cơ giới",
    "P.106a": "Cấm xe tải",
    "P.106b": "Cấm xe tải trên trọng tải",
    "P.106c": "Cấm xe kéo đẩy",
    "P.107": "Cấm ô tô khách và ô tô tải",
    "P.107a": "Cấm xe khách",
    "P.108": "Cấm xe kéo rơ moóc",
    "P.109": "Cấm xích lô",
    "P.110": "Cấm xe súc vật kéo",
    "P.111a": "Cấm xe ba bánh loại có động cơ",
    "P.112": "Cấm người đi bộ",
    "P.113": "Cấm xe thô sơ",
    "P.115": "Hạn chế trọng lượng",
    "P.116": "Hạn chế trọng lượng trục xe",
    "P.117": "Hạn chế chiều cao",
    "P.118": "Hạn chế chiều rộng",
    "P.119": "Hạn chế chiều dài",
    "P.121": "Cự ly tối thiểu giữa hai xe",
    "P.123a": "Cấm rẽ trái",
    "P.123b": "Cấm rẽ phải",
    "P.124a": "Cấm quay đầu",
    "P.124b": "Cấm quay đầu",
    "P.124c": "Cấm rẽ trái và quay đầu xe",
    "P.124d": "Cấm rẽ phải và quay đầu xe",
    "P.124e": "Cấm ô tô rẽ trái và quay đầu xe",
    "P.125": "Cấm vượt",
    "P.126": "Cấm xe ô tô tải vượt",
    "P.127": "Tốc độ tối đa",
    "P.128": "Cấm sử dụng còi",
    "P.130": "Cấm dừng/đỗ xe",
    "P.131": "Cấm đỗ xe",
    "P.131a": "Cấm đỗ xe ngày lẻ",
    "P.132": "Cấm dừng xe",
    "P.134": "Hết hạn chế tốc độ tối đa",
    "P.135": "Hết tất cả các lệnh cấm",
    "P.136": "Hết cấm còi",
    "P.137": "Cấm rẽ phải",
    "P.207a": "Biển cấm đặc biệt",
    "P.245a": "Đi chậm",
    "P.302": "Biển cấm khu vực",
    "P.302a": "Biển cấm khu vực (phụ)",
    # ── Biển hiệu lệnh / chỉ dẫn (R) ───────────────────────────
    "R.301a": "Hướng đi phải theo (đi thẳng)",
    "R.301c": "Hướng đi phải theo (rẽ trái)",
    "R.301d": "Hướng đi phải theo (rẽ phải)",
    "R.301e": "Hướng đi phải theo",
    "R.302a": "Đi vòng sang trái",
    "R.302b": "Đi vòng sang phải",
    "R.303": "Nơi giao nhau chạy theo vòng xuyến",
    "R.403a": "Đường dành cho xe ô tô",
    "R.407a": "Đường một chiều",
    "R.409": "Chỗ quay xe",
    "R.420": "Bắt đầu khu đông dân cư",
    "R.423b": "Đường người đi bộ sang ngang",
    "R.425": "Bệnh viện",
    "R.426": "Trạm cấp cứu",
    "R.434": "Bến xe buýt",
    # ── Biển chỉ dẫn (S) ────────────────────────────────────────
    "S.509a": "Biển chỉ dẫn",
    # ── Biển cảnh báo nguy hiểm (W) ─────────────────────────────
    "W.201a": "Chỗ ngoặt nguy hiểm (trái)",
    "W.201b": "Chỗ ngoặt nguy hiểm (phải)",
    "W.202a": "Nhiều chỗ ngoặt liên tiếp (trái)",
    "W.202b": "Nhiều chỗ ngoặt liên tiếp (phải)",
    "W.203b": "Đường dốc xuống",
    "W.203c": "Đường dốc lên",
    "W.205a": "Đường giao nhau",
    "W.205b": "Đường giao nhau (ngã ba bên phải)",
    "W.205c": "Đường giao nhau (ngã ba bên trái)",
    "W.205d": "Đường giao nhau (ngã ba)",
    "W.205e": "Đường giao nhau (ngã ba phía trước)",
    "W.206": "Giao nhau có tín hiệu đèn",
    "W.207a": "Giao nhau với đường không ưu tiên",
    "W.207b": "Giao nhau với đường không ưu tiên",
    "W.207c": "Giao nhau với đường không ưu tiên",
    "W.208": "Giao nhau với đường ưu tiên",
    "W.209": "Chỗ ngoặt nguy hiểm",
    "W.210": "Đường hẹp",
    "W.211": "Giao nhau với đường sắt không có rào chắn",
    "W.221a": "Đường không bằng phẳng",
    "W.221b": "Đường không phẳng (gồ giảm tốc)",
    "W.224": "Đường người đi bộ cắt ngang",
    "W.225": "Trẻ em",
    "W.226": "Đường người đi xe đạp cắt ngang",
    "W.227": "Công trường đang thi công",
    "W.228": "Đường trơn",
    "W.233": "Nguy hiểm khác",
    "W.239b": "Chiều cao tĩnh không thực tế",
    "W.243": "Nơi đường sắt giao không vuông góc với đường bộ",
    "W.245a": "Đi chậm",
    "W.302a": "Biển phụ (phạm vi tác dụng)",
    "W.423b": "Biển phụ (người đi bộ)",
    # ── Đèn giao thông ──────────────────────────────────────────
    "dendo": "Đèn đỏ",
    "denvang": "Đèn vàng",
    "denxanh": "Đèn xanh",
}

COLORS = {
    "P": (220, 53, 69),
    "DP": (255, 143, 0),
    "R": (13, 110, 253),
    "S": (25, 135, 84),
    "W": (255, 193, 7),
    "den": (108, 117, 125),
}


def get_color(class_name):
    for prefix, color in COLORS.items():
        if class_name.startswith(prefix):
            return color
    return (0, 255, 0)


@st.cache_resource
def load_model(model_path):
    model = torch.hub.load(
        "ultralytics/yolov5", "custom",
        path=os.path.abspath(model_path),
        force_reload=False,
    )
    return model


def draw_detections(image, df):
    img = image.copy()
    for _, row in df.iterrows():
        x1, y1 = int(row["xmin"]), int(row["ymin"])
        x2, y2 = int(row["xmax"]), int(row["ymax"])
        cls_name = row["name"]
        conf = row["confidence"]
        color = get_color(cls_name)

        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)

        label = f"{cls_name} {conf:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(img, (x1, y1 - th - 10), (x1 + tw + 4, y1), color, -1)
        cv2.putText(img, label, (x1 + 2, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    return img


def build_results_table(df):
    rows = []
    for _, row in df.iterrows():
        cls_name = row["name"]
        rows.append({
            "Mã biển": cls_name,
            "Ý nghĩa": SIGN_INFO.get(cls_name, "—"),
            "Độ tin cậy": f"{row['confidence']:.1%}",
            "Vị trí": f"({row['xmin']:.0f}, {row['ymin']:.0f}) → ({row['xmax']:.0f}, {row['ymax']:.0f})",
        })
    return rows


# ─── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Nhận diện biển báo giao thông Việt Nam",
    page_icon="🚦",
    layout="wide",
)

st.title("Nhận diện biển báo giao thông Việt Nam")
st.caption("YOLOv5 — Hỗ trợ ảnh, video và webcam")

# ─── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.header("Cài đặt")
    confidence = st.slider("Ngưỡng confidence", 0.0, 1.0, 0.25, 0.05)
    st.divider()
    st.markdown(
        "**Hướng dẫn**\n"
        "1. Chọn tab Ảnh / Video / Webcam\n"
        "2. Upload file hoặc chụp ảnh\n"
        "3. Xem kết quả nhận diện"
    )
    st.divider()
    st.markdown(f"**Model:** `best.pt`")
    st.markdown(f"**Số class:** {len(SIGN_INFO)}")

model = load_model("best.pt")
model.conf = confidence

# ─── Tabs ───────────────────────────────────────────────────────
tab_image, tab_video, tab_webcam = st.tabs(["📷 Ảnh", "🎬 Video", "📹 Webcam"])

# ─── Tab 1: Ảnh ────────────────────────────────────────────────
with tab_image:
    uploaded_img = st.file_uploader(
        "Upload ảnh", type=["jpg", "jpeg", "png", "bmp", "webp"],
        key="img_uploader",
    )

    if uploaded_img is not None:
        pil_img = Image.open(uploaded_img).convert("RGB")
        img_array = np.array(pil_img)

        with st.spinner("Đang nhận diện..."):
            results = model(img_array, size=640)
            df = results.pandas().xyxy[0]

        result_img = draw_detections(img_array, df)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Ảnh gốc")
            st.image(pil_img, use_container_width=True)
        with col2:
            st.subheader(f"Kết quả ({len(df)} biển báo)")
            st.image(result_img, use_container_width=True)

        if len(df) > 0:
            st.subheader("Chi tiết nhận diện")
            st.dataframe(build_results_table(df), use_container_width=True, hide_index=True)

            result_pil = Image.fromarray(result_img)
            import io
            buf = io.BytesIO()
            result_pil.save(buf, format="PNG")
            st.download_button(
                "Tải ảnh kết quả",
                data=buf.getvalue(),
                file_name="result.png",
                mime="image/png",
            )
        else:
            st.info("Không phát hiện biển báo nào trong ảnh.")

# ─── Tab 2: Video ──────────────────────────────────────────────
with tab_video:
    uploaded_vid = st.file_uploader(
        "Upload video", type=["mp4", "avi", "mov", "mkv", "m4a", "m4v", "webm"],
        key="vid_uploader",
    )

    if uploaded_vid is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uploaded_vid.read())
        tfile.flush()

        cap = cv2.VideoCapture(tfile.name)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        st.info(f"Video: {total_frames} frames, {fps:.0f} FPS, {w}x{h}")

        if st.button("Bắt đầu nhận diện video", key="start_video"):
            out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

            progress = st.progress(0, text="Đang xử lý...")
            frame_placeholder = st.empty()
            stats_placeholder = st.empty()

            total_detections = 0
            frame_id = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = model(rgb, size=640)
                df = results.pandas().xyxy[0]
                total_detections += len(df)

                annotated = draw_detections(rgb, df)
                bgr_out = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)
                writer.write(bgr_out)

                if frame_id % 5 == 0:
                    frame_placeholder.image(annotated, caption=f"Frame {frame_id}/{total_frames}", use_container_width=True)

                pct = min((frame_id + 1) / max(total_frames, 1), 1.0)
                progress.progress(pct, text=f"Frame {frame_id + 1}/{total_frames}")
                frame_id += 1

            cap.release()
            writer.release()

            progress.progress(1.0, text="Hoàn tất!")
            stats_placeholder.success(f"Đã xử lý {frame_id} frames. Tổng phát hiện: {total_detections} biển báo.")

            converted_path = out_path.replace(".mp4", "_h264.mp4")
            ret_code = os.system(f'ffmpeg -y -i "{out_path}" -vcodec libx264 "{converted_path}" -loglevel quiet')

            if ret_code == 0 and os.path.exists(converted_path):
                st.video(converted_path)
                with open(converted_path, "rb") as f:
                    st.download_button("Tải video kết quả", data=f.read(), file_name="result.mp4", mime="video/mp4")
                os.unlink(converted_path)
            else:
                st.video(out_path)
                with open(out_path, "rb") as f:
                    st.download_button("Tải video kết quả", data=f.read(), file_name="result.mp4", mime="video/mp4")

            os.unlink(out_path)

        cap.release()
        os.unlink(tfile.name)

# ─── Tab 3: Webcam ─────────────────────────────────────────────
with tab_webcam:
    camera_img = st.camera_input("Chụp ảnh từ webcam")

    if camera_img is not None:
        pil_img = Image.open(camera_img).convert("RGB")
        img_array = np.array(pil_img)

        with st.spinner("Đang nhận diện..."):
            results = model(img_array, size=640)
            df = results.pandas().xyxy[0]

        result_img = draw_detections(img_array, df)

        st.subheader(f"Kết quả ({len(df)} biển báo)")
        st.image(result_img, use_container_width=True)

        if len(df) > 0:
            st.dataframe(build_results_table(df), use_container_width=True, hide_index=True)
        else:
            st.info("Không phát hiện biển báo nào.")
