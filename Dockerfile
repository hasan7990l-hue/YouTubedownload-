FROM python:3.11-slim

# تثبيت أداة ffmpeg وتحديث النظام داخل الحاوية
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

WORKDIR /app

COPY . /app

# تثبيت المكتبات وتحديث yt-dlp لإصدار 2026 لتخطي الحظر
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade --force-reinstall yt-dlp

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
