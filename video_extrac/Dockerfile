FROM python:3.9

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy the application files
COPY requirements.txt requirements.txt
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Expose port 5000 for Flask
EXPOSE 5000

# Run the application
CMD ["python", "main.py"]
