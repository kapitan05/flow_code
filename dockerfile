FROM prefecthq/prefect:2.7.7-python3.9

COPY dokcer_requirements.txt .

RUN pip install -r dokcer_requirements.txt --trusted-host pypi.python.org --no-cache-dir
RUN mkdir -p /opt/prefect/data/yellow

COPY flows /opt/prefect/flows
COPY data /opt/prefect/data
