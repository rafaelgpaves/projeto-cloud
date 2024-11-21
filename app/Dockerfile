FROM python:3.11-bookworm

COPY ./requirements.txt ./requirements.txt
COPY ./main.py ./main.py

RUN python -m ensurepip --upgrade
RUN pip install -r ./requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
