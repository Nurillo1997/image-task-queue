# Image Task Queue

Asynchronous image processing service built with FastAPI, RabbitMQ, Celery, and PostgreSQL. Users upload an image and select an operation (resize, watermark, or grayscale); the API queues the job instead of blocking on it, a Celery worker picks it up and processes it, and the frontend polls for status until the result is ready to download.

## Why this architecture

Image processing can be slow, and a web request should never block on slow work. This project demonstrates the standard pattern for offloading work from a web API: accept the request, persist it, hand it to a message queue, and let a separate worker process do the heavy lifting. The API stays fast and responsive regardless of how long the actual processing takes, and workers can be scaled independently of the API itself.

The architecture is inspired by the FastAPI + RabbitMQ + Celery pattern used in [katanaml/katana-skipper](https://github.com/katanaml/katana-skipper), an ML workflow engine by Andrej Baranovskij. This project adapts that pattern to a simpler, self-contained domain (image processing instead of ML orchestration) and adds PostgreSQL for persistent task tracking, which the original project does not include.

## Architecture

\`\`\`
Browser (React)
      |
      v
FastAPI  ---->  PostgreSQL (task metadata + status)
      |
      v
  RabbitMQ (task queue)
      |
      v
Celery worker  ---->  Pillow (resize / watermark / grayscale)
      |
      v
PostgreSQL (status update: done / failed)
\`\`\`

1. The browser uploads an image and selects an operation.
2. FastAPI saves the file, writes a \`pending\` task row to PostgreSQL, and publishes a job to RabbitMQ. It responds immediately with a task ID.
3. A Celery worker consumes the queue, marks the task \`processing\`, runs the Pillow transformation, saves the result, and marks the task \`done\` (or \`failed\` with an error message if something goes wrong).
4. The frontend polls \`GET /status/{task_id}\` every two seconds until the task is no longer pending or processing, then offers a download link.

## Tech stack

- **Backend**: FastAPI, SQLAlchemy, Celery, Pillow
- **Queue**: RabbitMQ
- **Database**: PostgreSQL
- **Frontend**: React (Vite)
- **Infrastructure**: Docker, Docker Compose

## Running locally

Requirements: Docker and Docker Compose.

\`\`\`bash
git clone https://github.com/Nurillo1997/image-task-queue.git
cd image-task-queue
docker-compose up --build
\`\`\`

This starts five containers: PostgreSQL, RabbitMQ, the FastAPI API, the Celery worker, and the React frontend (served via nginx).

- Frontend: http://localhost:5173
- API docs (Swagger): http://localhost:8000/docs
- RabbitMQ management UI: http://localhost:15672 (guest / guest)

## API endpoints

| Method | Path | Description |
|---|---|---|
| POST | \`/api/v1/images/upload\` | Upload an image and queue a processing job. Accepts \`file\` (JPEG/PNG, max 10MB) and \`operation\` (\`resize\`, \`watermark\`, or \`grayscale\`) as form data. Returns a \`task_id\`. |
| GET | \`/api/v1/images/status/{task_id}\` | Returns the current status of a task (\`pending\`, \`processing\`, \`done\`, or \`failed\`). |
| GET | \`/api/v1/images/result/{task_id}\` | Returns the processed image once the task is \`done\`. |

## Known limitations

This project favors simplicity appropriate for a portfolio piece over the full rigor of a production system:

- Database tables are created automatically on startup (\`Base.metadata.create_all\`) rather than through a migration tool like Alembic. This is fine for a single-developer project but would not scale to a team or to schema changes over time.
- The Celery worker container runs as root inside Docker, which Celery itself warns against. A non-root user would be the production-correct setup.
- There is no authentication; any client can upload images or query any task by ID.

