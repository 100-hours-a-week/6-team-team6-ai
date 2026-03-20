FROM runpod/worker-v1-vllm:v2.11.3
WORKDIR /

COPY requirements.txt .

RUN pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . .

ENV HF_TOKEN=${HF_TOKEN}

CMD python3 -m vllm.entrypoints.openai.api_server \
    --model resfebel/billage-guard-v2-4bit \
    --quantization bitsandbytes \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 4096 \
    --limit-mm-per-prompt '{"image":1}' \
    --gpu-memory-utilization 0.9 \
    & python3 -u Llama_handler.py