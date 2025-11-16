FROM python:3.11-slim

WORKDIR /app

COPY req_mediapipe.txt .
RUN pip install --no-cache-dir -r req_mediapipe.txt

COPY . .

# RUN touch /app/database.db

EXPOSE 5000

CMD ["python", "main.py"]
