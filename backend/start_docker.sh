#!/bin/bash
gunicorn --log-level INFO -b 0.0.0.0:8000 -w 1 -k uvicorn.workers.UvicornWorker app.main:app