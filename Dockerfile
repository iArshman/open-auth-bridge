FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY index.py .

# We don't COPY .env because you should pass env vars 
# via docker-compose or -e flags for security.

EXPOSE 3000

CMD ["python", "index.py"]
