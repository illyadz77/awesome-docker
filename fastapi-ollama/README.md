## Compose sample application
### Python/FastAPI application with Ollama (Local LLM Inference)

Project structure:
```
.
├── Dockerfile
├── README.md
├── app
│   ├── __init__.py
│   └── main.py
├── compose.yaml
└── requirements.txt
```

[_compose.yaml_](compose.yaml)
```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    # Uncomment below to enable NVIDIA GPU acceleration (requires NVIDIA Container Toolkit)
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]

  web:
    build: .
    container_name: fastapi-ollama
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - DEFAULT_MODEL=llama3.2:1b
    ports:
      - "8000:8000"
    depends_on:
      - ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

## Deploy with Docker Compose

1. Start the services with Docker Compose:

```console
$ docker compose up -d --build
```

2. Check that containers are up and running:

```console
$ docker compose ps
NAME             IMAGE                  COMMAND               SERVICE   CREATED          STATUS          PORTS
fastapi-ollama   fastapi-ollama-web     "uvicorn app.main:…"  web       10 seconds ago   Up 9 seconds    0.0.0.0:8000->8000/tcp
ollama           ollama/ollama:latest   "/bin/ollama serve"   ollama    10 seconds ago   Up 9 seconds    0.0.0.0:11434->11434/tcp
```

3. Pull a model into the Ollama container (e.g. `llama3.2:1b` or any model supported by Ollama):

```console
$ docker compose exec ollama ollama pull llama3.2:1b
```

> **Note**: Models are saved into the persistent volume `ollama_data`, so they remain available across restarts.

## Expected Result

Navigate to `http://localhost:8000` in your web browser or run:

```console
$ curl http://localhost:8000/
{"status":"online","service":"FastAPI + Ollama Sample","ollama_host":"http://ollama:11434","default_model":"llama3.2:1b","docs_url":"/docs"}
```

### Test Text Generation

Send a prompt to `/generate`:

```console
$ curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Why is Docker useful in one sentence?"}'
```

Response:
```json
{
  "model": "llama3.2:1b",
  "response": "Docker packages applications and dependencies into standardized containers, ensuring consistent execution across any environment."
}
```

### Test Streaming Generation

Send a streaming prompt to `/generate`:

```console
$ curl -N -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Count to 5", "stream": true}'
```

### Interactive API Documentation

Visit `http://localhost:8000/docs` to test all endpoints interactively via Swagger UI.

## GPU Acceleration (Optional)

To run Ollama with NVIDIA GPU acceleration for faster inference:
1. Ensure the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) is installed on your host system.
2. In `compose.yaml`, uncomment the `deploy` reservation block under the `ollama` service:
   ```yaml
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: all
             capabilities: [gpu]
   ```
3. Restart the stack:
   ```console
   $ docker compose up -d
   ```

## Stop and remove the containers

```console
$ docker compose down
```

To also remove the persisted model data:

```console
$ docker compose down -v
```
