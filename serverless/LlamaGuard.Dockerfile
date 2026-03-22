ARG CACHE_BUST=20260321_v4
FROM runpod/worker-v1-vllm:v2.11.3
WORKDIR /

COPY requirements.txt .

RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir --upgrade -r requirements.txt && \
    python3 -c "import transformers; print('### transformers version:', transformers.__version__)"

COPY . .

ENV HF_TOKEN=${HF_TOKEN}
#ENV VLLM_NIGHTLY=true

CMD python3 -m vllm.entrypoints.openai.api_server \
    --model resfebel/billage-guard-v2-4bit \
    --quantization bitsandbytes \
    --load-format bitsandbytes \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 4096 \
    --limit-mm-per-prompt image=1 \
    --gpu-memory-utilization 0.9 \
    2>&1 | tee /var/log/vllm.log \
    & python3 -u Llama_handler.py