import asyncio
import os

import httpx
import runpod


VLLM_API_KEY = os.environ.get("VLLM_API_KEY")

# 엔진 준비 확인
async def wait_for_vllm():
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {VLLM_API_KEY}"}
        while True:
            try:
                response = await client.get(
                    "http://127.0.0.1:8000/v1/models", headers=headers, timeout=1.0
                )
                if response.status_code == 200:
                    print("vLLM 엔진이 성공적으로 준비되었습니다!", flush=True)
                    break
                elif response.status_code == 401:
                    print(">>> 인증 에러 발생! API 키를 다시 확인하세요.", flush=True)
            except Exception:
                pass
            print("vLLM 엔진 로딩 중... (8000번 포트 대기 중)", flush=True)
            await asyncio.sleep(5)  # 5초마다 재시도

asyncio.run(wait_for_vllm())

async def handler(job):
    print("Llama 핸들러 호출 완료")
    job_input = job.get("input", {})
    headers = {"Authorization": f"Bearer {VLLM_API_KEY}"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://127.0.0.1:8000/v1/chat/completions",
                json=job_input,
                headers=headers,
                timeout=120,
            )
            result = response.json()
            # content만 : 서버리스는 output에서 찾도록
            choices = result.get("choices")

            if not choices:
                raise Exception(f"모델 응답 형식이 올바르지 않습니다: {choices}")
            try:
                validate_output = choices[0]["message"]["content"].strip()
                print(f"응답 원본: {validate_output}")

                if "unsafe" in validate_output:
                    output_parts = validate_output.split()

                    policy_code = output_parts[-1] if len(output_parts) > 1 else "safe"

                    return {
                        "is_safe" : "unsafe",
                        "policy_code" : policy_code
                    }
                else:
                    return { "is_safe" : "safe" }

            except Exception as e:
                return { "error" : f"모델 응답 중 에러: {str(e)}"}

        except Exception as e:
            return {"error": f"vLLM Proxy 에러: {e}"}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
