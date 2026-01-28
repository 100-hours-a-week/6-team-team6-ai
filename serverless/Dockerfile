FROM runpod/worker-v1-vllm:v2.11.3
WORKDIR /
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod
COPY . .
CMD [ "python", "-u", "/serverless/handler.py" ]