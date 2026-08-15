FROM python:3.12-slim
WORKDIR /srv/app
RUN useradd --create-home --shell /usr/sbin/nologin ctf
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
USER ctf
EXPOSE 8080
CMD ["gunicorn","--workers","4","--threads","8","--bind","0.0.0.0:8080","app:create_app()"]
