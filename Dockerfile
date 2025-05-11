# Stage 1: Build (using a full development environment)
FROM python:3.12 AS builder
RUN pip install --user some-package

# Stage 2: Final run image (keep only necessary files)
FROM python:3.12-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy the project into the container
# COPY . /app
COPY *.py /app/
COPY *.json /data/
WORKDIR /app

# Install necessary packages
#RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8001
#CMD uvicorn main:app --host=0.0.0.0 --port=8080
# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]