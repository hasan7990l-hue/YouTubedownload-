FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# تثبيت FFmpeg وتحديث النظام بالكامل
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# نسخ ملف المتطلبات
COPY ./requirements.txt /code/requirements.txt

# تحديث pip وتثبيت المكتبات، مع إجبار ترقية yt-dlp لآخر تحديث متوفر لمنع الحظر
RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt && \
    pip install --no-cache-dir --upgrade yt-dlp

# نسخ باقي ملفات المشروع
COPY . .

# إنشاء مجلد التحميلات ومجلد الجلسات وإعطائهما صلاحيات كاملة
RUN mkdir -p /code/downloads && chmod 777 /code/downloads

# فتح البورت المتوافق مع معظم الاستضافات الحديثة (مثل Hugging Face التي تفضل 7860 أو Render 10000)
# ملاحظة: يمكنك تركه 5000 إذا كنت قد ضبطت الاستضافة لقراءة بورت 5000
EXPOSE 7860

# تشغيل التطبيق
CMD ["python", "app.py"]
