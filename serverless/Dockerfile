FROM runpod/worker-v1-vllm:v2.11.3
WORKDIR /

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir runpod
COPY . .

# 핸들러 요청
#CMD ["python3", "-u", "serverless/handler.py"]
CMD python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-VL-7B-Instruct \
    --max-model-len 4096 \
    --enforce-eager \
    --limit-mm-per-prompt image=5 \
    --gpu-memory-utilization 0.9 \
    & python3 -u serverless/handler.py