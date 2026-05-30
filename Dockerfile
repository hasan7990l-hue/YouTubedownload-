FROM python:3.10-slim

# تثبيت أداة ffmpeg لمعالجة الصوت والفيديو داخل السيرفر
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /lib/apt/lists/*

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

CMD ["python", "app.py"]
