# Detection Pipeline
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and video processing
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU version of PyTorch first to save 3.5GB of useless downloads!
RUN pip install torch==2.2.2 torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cpu

RUN pip install numpy==1.26.4 && pip install --default-timeout=1000 -r requirements.txt

# Pre-download YOLOv8n model
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

COPY . .

RUN mkdir -p /logs /models

CMD ["python", "main.py"]
