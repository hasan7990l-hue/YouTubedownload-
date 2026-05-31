FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# تثبيت FFmpeg وتحديث النظام
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# نسخ ملف المتطلبات أولاً لتسريع عملية البناء (Caching)
COPY ./requirements.txt /code/requirements.txt

# تحديث pip وتثبيت المكتبات
RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt

# نسخ باقي ملفات المشروع
COPY . .

# إنشاء مجلد التحميلات وإعطائه صلاحيات كاملة تجنباً لمشاكل الـ Permission
RUN mkdir -p /code/downloads && chmod 777 /code/downloads

# فتح البورت 5000 المتوافق مع الفلاكس
EXPOSE 5000

CMD ["python", "app.py"]
