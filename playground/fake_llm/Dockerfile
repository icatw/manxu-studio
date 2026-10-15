FROM python:3.13-slim
WORKDIR /app
COPY server.py ./
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"
CMD ["python", "server.py"]
