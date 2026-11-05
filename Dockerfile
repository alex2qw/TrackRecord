FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["flask", "--app", "trackrecord.app:create_app", "run", "--host=0.0.0.0", "--port=8000"]
