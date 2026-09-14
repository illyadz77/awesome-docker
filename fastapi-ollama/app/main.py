import os
import json
from typing import Optional, List, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from pydantic import BaseModel

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2:1b")

http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(
        base_url=OLLAMA_HOST,
        timeout=httpx.Timeout(120.0, connect=10.0),
    )
    yield
    await http_client.aclose()


app = FastAPI(
    title="FastAPI + Ollama Compose Sample",
    description="Sample application integrating FastAPI with Ollama for local LLM inference.",
    version="1.0.0",
    lifespan=lifespan,
)


def get_client() -> httpx.AsyncClient:
    if http_client is None or http_client.is_closed:
        raise HTTPException(status_code=503, detail="HTTP client is not initialized")
    return http_client


class GenerateRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    stream: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    stream: bool = False


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "FastAPI + Ollama Sample",
        "ollama_host": OLLAMA_HOST,
        "default_model": DEFAULT_MODEL,
        "docs_url": "/docs",
    }


@app.get("/models")
async def list_models():
    """List all available models pulled in Ollama."""
    client = get_client()
    try:
        response = await client.get("/api/tags")
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Ollama error: {response.text}",
            )
        return response.json()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to connect to Ollama service at {OLLAMA_HOST}: {exc}",
        )


async def stream_ollama_response(response: httpx.Response) -> AsyncGenerator[bytes, None]:
    try:
        async for chunk in response.aiter_bytes():
            yield chunk
    except httpx.RequestError as exc:
        error_msg = f"{json.dumps({'error': f'Network error during streaming: {exc}'})}\n"
        yield error_msg.encode("utf-8")
    finally:
        await response.aclose()


@app.post("/generate")
async def generate_text(request: GenerateRequest):
    """Generate completion from a prompt using local Ollama model."""
    client = get_client()
    model = request.model or DEFAULT_MODEL
    payload = {
        "model": model,
        "prompt": request.prompt,
        "stream": request.stream,
    }

    if request.stream:
        try:
            req = client.build_request("POST", "/api/generate", json=payload)
            response = await client.send(req, stream=True)
            if response.status_code != 200:
                error_detail = await response.aread()
                await response.aclose()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail.decode("utf-8", errors="replace"),
                )
            return StreamingResponse(
                stream_ollama_response(response),
                media_type="application/x-ndjson",
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Error communicating with Ollama: {exc}",
            )

    try:
        response = await client.post("/api/generate", json=payload)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text,
            )
        return response.json()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Error communicating with Ollama: {exc}",
        )


@app.post("/chat")
async def chat_completion(request: ChatRequest):
    """Chat completion using local Ollama model."""
    client = get_client()
    model = request.model or DEFAULT_MODEL
    payload = {
        "model": model,
        "messages": [m.model_dump() for m in request.messages],
        "stream": request.stream,
    }

    if request.stream:
        try:
            req = client.build_request("POST", "/api/chat", json=payload)
            response = await client.send(req, stream=True)
            if response.status_code != 200:
                error_detail = await response.aread()
                await response.aclose()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail.decode("utf-8", errors="replace"),
                )
            return StreamingResponse(
                stream_ollama_response(response),
                media_type="application/x-ndjson",
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Error communicating with Ollama: {exc}",
            )

    try:
        response = await client.post("/api/chat", json=payload)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text,
            )
        return response.json()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Error communicating with Ollama: {exc}",
        )
