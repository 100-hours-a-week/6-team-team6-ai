FROM runpod/worker-v1-vllm:v2.11.3
WORKDIR /

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .

ENV HF_TOKEN=${HF_TOKEN}

CMD python3 -m vllm.entrypoints.openai.api_server $VLLM_ARGS & python3 -u handler.py