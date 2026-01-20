FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy monitor script
COPY monitor.py .

# Create log directory with proper permissions
RUN mkdir -p /app/logs && chmod 755 /app/logs && chmod +x monitor.py

# Run the monitor (use unbuffered output for better logging)
CMD ["python", "-u", "monitor.py"]
