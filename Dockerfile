# Base image chính thức của Python
FROM python:3.11-slim

# Tạo thư mục làm việc
WORKDIR /app

# Copy mã nguồn vào container
COPY . /app

# Cài đặt các thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Expose cổng Flask (mặc định 5000)
EXPOSE 5000

# Biến môi trường để chạy Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Lệnh chạy Flask
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "app:app"]
