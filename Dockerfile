FROM python:3.11-slim

# تثبيت أداة ffmpeg وتحديث النظام داخل الحاوية مع حزم إضافية لضمان عمل الشبكة واستقرار الاتصال
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

# تثبيت المكتبات وتحديث yt-dlp لإصدار 2026 لتخطي الحظر
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade --force-reinstall yt-dlp

# كشف المنفذ الخاص بـ Streamlit لكي يعمل خادم الويب بدون توقف
EXPOSE 8501

# إعداد المتغيرات البيئية لمنع تجميد أو تعليق الـ Logs الخاصة بـ Telethon و Streamlit بالداخل
ENV PYTHONUNBUFFERED=1

# أمر تشغيل خادم ويب Streamlit وبوت التليجرام معاً
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
