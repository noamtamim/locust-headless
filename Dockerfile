FROM python:buster

RUN pip install -U pip wheel && pip install locust boto3 pyyaml

RUN echo >> /etc/security/limits.conf && \
    echo "locust  soft  nofile 50000" >> /etc/security/limits.conf && \
    echo "locust  hard  nofile 50000" >> /etc/security/limits.conf && \
    echo "fs.file-max=500000" > /etc/sysctl.d/local.conf

WORKDIR /locust
COPY entrypoint.py .
RUN chmod +x entrypoint.py
ENTRYPOINT ["./entrypoint.py"]

# turn off python output buffering
ENV PYTHONUNBUFFERED=1
