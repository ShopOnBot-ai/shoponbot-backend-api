# Docker Execution Flow (Step-by-Step)

## Command

```bash
docker compose up --build
```

This command performs two tasks:

* `--build` → Builds the Docker image from the Dockerfile.
* `up` → Creates and starts all containers defined in `docker-compose.yml`.

---

# Complete Execution Flow

## Step 1. Docker Compose Reads `docker-compose.yml`

Docker Compose is always the entry point.

It reads the `docker-compose.yml` file and discovers all services that need to be started.

Example:

```yaml
services:
  web:
  redis:
  db:
```

Here, Docker Compose knows it needs to create three services:

* Web (FastAPI)
* Redis
* PostgreSQL

---

## Step 2. Docker Compose Processes Each Service

For every service, Docker Compose checks whether it should:

* Build an image from a Dockerfile
* Or use an existing image from Docker Hub

Example:

```yaml
web:
  build: .
```

means

> Build the image using the Dockerfile in the current directory.

Example:

```yaml
redis:
  image: redis:alpine
```

means

> Pull the Redis image directly from Docker Hub.

---

# Dockerfile Build Process

Dockerfile is **not executed directly**.

Docker Compose instructs Docker Engine to execute it.

---

## Step 3. Base Image (`FROM`)

```dockerfile
FROM python:3.12-slim
```

Docker checks whether this image already exists locally.

If not, it downloads it from Docker Hub.

This image becomes the base layer for our application.

---

## Step 4. Temporary Build Container

To execute Dockerfile instructions, Docker creates a temporary container.

Every Dockerfile instruction executes inside this temporary container.

This container exists only during the image build process.

---

## Step 5. Environment Variables

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
```

These environment variables become part of the Docker image.

They are available whenever a container is created from this image.

---

## Step 6. Install Dependencies

```dockerfile
RUN pip install uv
```

Runs inside the temporary container.

Equivalent to:

```bash
pip install uv
```

---

## Step 7. Working Directory

```dockerfile
WORKDIR /app
```

Equivalent to:

```bash
mkdir /app
cd /app
```

All subsequent commands execute inside `/app`.

---

## Step 8. Copy Project Files

```dockerfile
COPY . .
```

Copies the project from the host machine into the container.

```
Host Machine
      │
      ▼
Current Project
      │
      ▼
Container (/app)
```

---

## Step 9. Install Project Packages

```dockerfile
RUN uv sync --frozen
```

Installs all project dependencies from `uv.lock`.

This makes the image self-contained.

---

## Step 10. Expose Port

```dockerfile
EXPOSE 8000
```

This **does not** publish the port.

It only documents that the application inside the container uses port `8000`.

---

## Step 11. Default Startup Command

```dockerfile
CMD ["uv", "run", "uvicorn", ...]
```

This command is **not executed during image build**.

It is simply stored inside the image.

It will run only when a container starts.

---

# Docker Image Created

After all Dockerfile instructions finish:

* Temporary build container is deleted.
* A Docker Image is created.

```
Dockerfile
      │
      ▼
Docker Image
```

The image is read-only and reusable.

---

# Container Creation

## Step 12. Create Running Container

Docker Compose now creates a running container from the image.

```
Docker Image
      │
      ▼
Running Container
```

This is where the FastAPI application actually runs.

---

# Volume Mounting

## Step 13. Mount Host Directory

```yaml
volumes:
  - .:/app
```

Maps the host project into the container.

```
Host Project
      │
      ▼
Container (/app)
```

Benefits:

* Live code updates
* No rebuild required after every code change
* Uvicorn reload works automatically

---

## Anonymous Volume

```yaml
- /app/.venv
```

Creates a separate container-managed volume for `.venv`.

This prevents the host virtual environment from overwriting the Linux virtual environment inside the container.

---

# Docker Network

## Step 14. Create Internal Network

Docker Compose automatically creates a bridge network.

Example:

```
project_default
```

Every service joins this network.

```
Web
 │
Redis
 │
PostgreSQL
```

Now services communicate using service names.

Example:

```
redis
db
```

instead of IP addresses.

---

# Redis Container

Docker Compose sees:

```yaml
image: redis:alpine
```

Flow:

```
Docker Hub
      │
      ▼
Redis Image
      │
      ▼
Redis Container
```

No Dockerfile is required.

---

# PostgreSQL Container

Similarly:

```yaml
image: postgres:17-alpine
```

Flow:

```
Docker Hub
      │
      ▼
PostgreSQL Image
      │
      ▼
PostgreSQL Container
```

---

# Persistent Database Storage

```yaml
volumes:
    postgres_data:/var/lib/postgresql/data
```

Creates a named Docker volume.

Purpose:

* Database survives container recreation.
* Data remains even if the PostgreSQL container is deleted.

---

# Container Startup Order

```yaml
depends_on:
  - redis
  - db
```

This ensures:

1. Redis container starts.
2. PostgreSQL container starts.
3. Web container starts.

**Note:** `depends_on` only controls startup order. It does **not** guarantee that Redis or PostgreSQL are fully ready to accept connections. In production, health checks or retry logic are typically used.

---

# Application Startup

Finally Docker executes:

```dockerfile
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

Now:

* Uvicorn starts.
* FastAPI application loads.
* Database connection is established.
* Redis connection is established.
* Application begins serving requests.

---

# Complete Flow Diagram

```
docker compose up --build
            │
            ▼
Read docker-compose.yml
            │
            ▼
Identify all services
            │
            ▼
Build Docker Image (if build: .)
            │
            ▼
Execute Dockerfile
            │
            ▼
FROM
ENV
WORKDIR
COPY
RUN
RUN
EXPOSE
CMD (stored only)
            │
            ▼
Docker Image Created
            │
            ▼
Temporary Build Container Deleted
            │
            ▼
Create Internal Network
            │
            ▼
Create Named Volumes
            │
            ▼
Start Redis Container
            │
            ▼
Start PostgreSQL Container
            │
            ▼
Create Web Container
            │
            ▼
Mount Volumes
            │
            ▼
Execute CMD
            │
            ▼
Uvicorn Starts
            │
            ▼
FastAPI Application Running
```

---

# Key Concepts

| Component        | Purpose                                                  |
| ---------------- | -------------------------------------------------------- |
| Dockerfile       | Defines how to build an image                            |
| Docker Image     | Read-only blueprint of the application                   |
| Docker Container | Running instance of an image                             |
| Docker Compose   | Orchestrates multiple containers                         |
| Volume           | Persists data or shares files between host and container |
| Network          | Enables communication between containers                 |
| `depends_on`     | Controls startup order (not readiness)                   |
| CMD              | Default command executed when the container starts       |
| EXPOSE           | Documents the application's listening port               |

---

# Summary

* Docker Compose is the entry point.
* Dockerfile is used only to build the image.
* Docker creates a temporary build container while building the image.
* After the image is built, the temporary container is deleted.
* Docker Compose creates running containers from images.
* Volumes provide live code syncing and persistent storage.
* Docker automatically creates an internal network for service communication.
* `CMD` runs only after the container starts.
* The FastAPI application becomes available only after all previous steps complete successfully.


* RUN Scripts files using 
<!-- to create fake products -->
docker exec -it fastapi_app uv run python -m scripts.seed_products
<!-- to convert normal user to admin -->
docker exec -it fastapi_app uv run python -m scripts.provision_admin