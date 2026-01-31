FROM runpod/worker-v1-vllm:v2.11.3
WORKDIR /

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir runpod
COPY . .

# 핸들러 요청
CMD ["python3", "-u", "serverless/handler.py"]