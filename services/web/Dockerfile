FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY . .
RUN useradd --system --uid 10002 taskify
USER taskify
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"
CMD ["gunicorn", "taskify_web.wsgi", "--bind", "0.0.0.0:8000", "--worker-class", "gthread", "--threads", "16"]
