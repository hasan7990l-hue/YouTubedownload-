FROM python:3.10-slim

# تثبيت أداة ffmpeg لمعالجة الصوت والفيديو داخل السيرفر
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

# تحديث الـ pip أولاً ثم تثبيت المكتبات لتفادي التحذيرات ومشاكل الأذونات
RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt

COPY . .

# تشغيل البوت باستخدام ملف app.py
CMD ["python", "app.py"]
