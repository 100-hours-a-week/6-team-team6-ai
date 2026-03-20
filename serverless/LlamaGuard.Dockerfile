FROM runpod/worker-v1-vllm:v2.11.3
WORKDIR /

COPY requirements.txt .
# [중요] bitsandbytes 라이브러리가 도커 내에 반드시 설치되어 있어야 합니다.
RUN pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . .

ENV HF_TOKEN=${HF_TOKEN}

# 빌리지 보안관 v2-4bit 전용 설정
CMD python3 -m vllm.entrypoints.openai.api_server \
    --model resfebel/billage-guard-v2-4bit \
    --quantization bitsandbytes \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 4096 \
    --limit-mm-per-prompt '{"image":1}' \
    --gpu-memory-utilization 0.9 \
    & python3 -u Llama_handler.py