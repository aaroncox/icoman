FROM python:3.5.3-slim

RUN apt-get update && apt-get install -y make gcc libssl-dev

# Create the temp file with requirements and install
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

COPY . /src

CMD ["python", "/src/manager.py"]
