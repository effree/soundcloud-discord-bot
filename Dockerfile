FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# Run the script on a continuous loop or cron-like timer (e.g., every 10 minutes)
CMD ["python", "-u", "bot.py"]