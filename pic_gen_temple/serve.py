"""Z-Image single-worker inference service."""

import asyncio
import base64
import io
import json
import os
import queue
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "2")

import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from utils import AttentionBackend, ensure_model_weights, load_from_local_dir, set_attention_backend
from zimage import generate

app = FastAPI()


class GenRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    height: int = 1024
    width: int = 1024
    num_inference_steps: int = 8
    guidance_scale: float = 0.0
    seed: int = 42
    attn_backend: str = "_native_flash"
    output_dir: str = "outputs"
    output_name: Optional[str] = None


@dataclass
class Job:
    job_id: str
    request: GenRequest
    progress_queue: queue.Queue
    future: asyncio.Future


components: Dict[str, Any] = {}
device: Any = "cpu"
dtype = torch.bfloat16
jobs: Dict[str, Job] = {}
job_queue: asyncio.Queue = asyncio.Queue()


def _select_device() -> Any:
    if torch.cuda.is_available():
        return "cuda"
    try:
        import torch_xla.core.xla_model as xm

        return xm.xla_device()
    except (ImportError, RuntimeError):
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"


def _encode_base64(image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _emit_progress(progress_queue: queue.Queue, payload: Dict[str, Any]) -> None:
    progress_queue.put(payload)


def _run_job(job: Job) -> Dict[str, Any]:
    req = job.request
    set_attention_backend(req.attn_backend)
    os.makedirs(req.output_dir, exist_ok=True)
    output_name = req.output_name or f"zimage_{int(time.time() * 1000)}.png"
    output_path = os.path.join(req.output_dir, output_name)

    def progress_callback(step: int, total: int, t_norm: float) -> None:
        percent = round(step / total * 100, 2) if total else 0.0
        _emit_progress(
            job.progress_queue,
            {
                "type": "progress",
                "job_id": job.job_id,
                "step": step,
                "total": total,
                "percent": percent,
                "t_norm": round(t_norm, 6),
            },
        )

    with torch.inference_mode():
        start_time = time.time()
        images = generate(
            prompt=req.prompt,
            **components,
            height=req.height,
            width=req.width,
            num_inference_steps=req.num_inference_steps,
            guidance_scale=req.guidance_scale,
            generator=torch.Generator(device).manual_seed(req.seed),
            progress_callback=progress_callback,
        )
        elapsed = time.time() - start_time

    images[0].save(output_path)
    image_base64 = _encode_base64(images[0])

    _emit_progress(
        job.progress_queue,
        {
            "type": "complete",
            "job_id": job.job_id,
            "output_path": output_path,
            "time_sec": round(elapsed, 3),
        },
    )

    return {
        "output_path": output_path,
        "base64": image_base64,
        "time_sec": round(elapsed, 3),
    }


async def _worker() -> None:
    while True:
        job = await job_queue.get()
        try:
            result = await asyncio.to_thread(_run_job, job)
            job.future.set_result(result)
        except Exception as exc:
            _emit_progress(
                job.progress_queue,
                {
                    "type": "error",
                    "job_id": job.job_id,
                    "message": str(exc),
                },
            )
            job.future.set_exception(exc)
        finally:
            job_queue.task_done()


def _build_job(req: GenRequest, loop: asyncio.AbstractEventLoop) -> Job:
    job_id = str(uuid.uuid4())
    progress_queue: queue.Queue = queue.Queue()
    future: asyncio.Future = loop.create_future()
    job = Job(job_id=job_id, request=req, progress_queue=progress_queue, future=future)
    jobs[job_id] = job
    return job


@app.on_event("startup")
async def startup() -> None:
    global components, device, dtype

    model_path = ensure_model_weights(
        "/mnt/tmp/shenyh/officialWeights/Z-Image-Turbo", verify=False
    )
    device = _select_device()
    components = load_from_local_dir(model_path, device=device, dtype=dtype, compile=False)
    AttentionBackend.print_available_backends()

    asyncio.create_task(_worker())


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "device": str(device), "queue_size": job_queue.qsize()}


@app.get("/progress/{job_id}")
async def progress_stream(job_id: str) -> StreamingResponse:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_id not found")

    async def event_stream():
        while True:
            payload = await asyncio.to_thread(job.progress_queue.get)
            yield f"data: {json.dumps(payload)}\n\n"
            if payload.get("type") in {"complete", "error"}:
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/result/{job_id}")
async def get_result(job_id: str) -> Dict[str, Any]:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_id not found")
    if not job.future.done():
        return {"status": "running", "job_id": job_id}
    try:
        result = job.future.result()
    except Exception as exc:
        return {"status": "error", "job_id": job_id, "message": str(exc)}
    return {"status": "done", "job_id": job_id, **result}


@app.post("/generate")
async def generate_image(req: GenRequest) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    job = _build_job(req, loop)
    await job_queue.put(job)
    result = await job.future
    result["job_id"] = job.job_id
    return result


@app.post("/generate_async")
async def generate_async(req: GenRequest) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    job = _build_job(req, loop)
    await job_queue.put(job)
    return {"job_id": job.job_id, "status": "queued"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=6000)