ARG CACHE_BUST=20260322_v3
FROM runpod/worker-v1-vllm:v2.11.3
WORKDIR /

COPY requirements.txt .

RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir --force-reinstall -r requirements.txt

COPY . .

ENV HF_TOKEN=${HF_TOKEN}

CMD python3 -m vllm.entrypoints.openai.api_server \
    --model resfebel/billage-guard-v3-4bit \
    --quantization bitsandbytes \
    --load-format bitsandbytes \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 1024 \
    --limit-mm-per-prompt image=1 \
    --gpu-memory-utilization 0.95 \
    2>&1 | tee /var/log/vllm.log \
    & python3 -u Llama_handler.py