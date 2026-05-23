"""Z-Image diffusers single-worker inference service."""

import asyncio
import base64
import inspect
import io
import json
import os
import queue
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

import torch
from diffusers import ZImagePipeline
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI()


class GenRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    negative_prompt: Optional[str] = ""
    height: int = 1280
    width: int = 720
    num_inference_steps: int = 50
    guidance_scale: float = 4.0
    cfg_normalization: bool = False
    seed: int = 42
    attn_backend: Optional[str] = None
    output_dir: str = "outputs"
    output_name: Optional[str] = None


@dataclass
class Job:
    job_id: str
    request: GenRequest
    progress_queue: queue.Queue
    future: asyncio.Future


pipe: Optional[ZImagePipeline] = None
pipe_device: str = "cpu"
jobs: Dict[str, Job] = {}
job_queue: asyncio.Queue = asyncio.Queue()


def _select_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    try:
        import torch_xla.core.xla_model as xm

        return str(xm.xla_device())
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


def _timestep_to_float(timestep: Any) -> float:
    try:
        return float(timestep.item())
    except Exception:
        return float(timestep)


def _run_job(job: Job) -> Dict[str, Any]:
    assert pipe is not None
    req = job.request

    if req.attn_backend:
        pipe.transformer.set_attention_backend(req.attn_backend)

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

    call_kwargs: Dict[str, Any] = {
        "prompt": req.prompt,
        "negative_prompt": req.negative_prompt,
        "height": req.height,
        "width": req.width,
        "cfg_normalization": req.cfg_normalization,
        "num_inference_steps": req.num_inference_steps,
        "guidance_scale": req.guidance_scale,
        "generator": torch.Generator(pipe_device).manual_seed(req.seed),
    }

    sig = inspect.signature(pipe.__call__)
    if "callback_on_step_end" in sig.parameters:
        def on_step_end(_pipe, step, timestep, callback_kwargs):
            progress_callback(step + 1, req.num_inference_steps, _timestep_to_float(timestep))
            return callback_kwargs

        call_kwargs["callback_on_step_end"] = on_step_end
    elif "callback" in sig.parameters:
        def callback(step, timestep, latents):
            progress_callback(step + 1, req.num_inference_steps, _timestep_to_float(timestep))

        call_kwargs["callback"] = callback
        if "callback_steps" in sig.parameters:
            call_kwargs["callback_steps"] = 1
    else:
        progress_callback(0, req.num_inference_steps, 0.0)

    with torch.inference_mode():
        start_time = time.time()
        result = pipe(**call_kwargs)
        elapsed = time.time() - start_time

    image = result.images[0]
    image.save(output_path)
    image_base64 = _encode_base64(image)

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
    global pipe, pipe_device

    model_path = os.environ.get("ZIMAGE_DIFFUSERS_MODEL_PATH", "/mnt/tmp/shenyh/officialWeights/Z-Image")
    pipe_device = _select_device()

    pipe = ZImagePipeline.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=False,
    )
    pipe.to(pipe_device)

    asyncio.create_task(_worker())


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "device": str(pipe_device), "queue_size": job_queue.qsize()}


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

    uvicorn.run(app, host="0.0.0.0", port=6001)
