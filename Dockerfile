FROM python:3.11-slim

# تثبيت الحزم الأساسية وتحديث النظام داخل الحاوية لضمان استقرار الاتصال والشبكة
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

# تحديث أداة التثبيت وتثبيت مكتبات البوت (Streamlit و Telethon و Cryptography)
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# كشف المنفذ الخاص بـ Streamlit لكي يعمل خادم الويب بدون توقف وتظهر الواجهة في الكلاود
EXPOSE 8501

# إعداد المتغيرات البيئية لمنع تجميد أو تعليق الـ Logs الخاصة بـ Telethon و Streamlit بالداخل
ENV PYTHONUNBUFFERED=1

# أمر تشغيل خادم ويب Streamlit وبوت التليجرام معاً في الخلفية
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
