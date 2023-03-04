import pandas as pd
from sqlalchemy import create_engine
import os
from time import time
from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta
from prefect_sqlalchemy import SqlAlchemyConnector

@task(log_prints=True, retries=3, cache_key_fn=task_input_hash, cache_expiration=timedelta(days=1))
def extract_data(url):
    parquet_name = 'output.csv'

    os.system(f'wget {url} -O {parquet_name}')

    df = pd.read_parquet(parquet_name, engine='pyarrow')

    return df

@task(log_prints=True)
def transform_data(df):
    print(f"pre: missing passenger count: {df['passenger_count'].isin([0]).sum()}")
    df = df[df['passenger_count'] != 0]
    print(f'post: missing passenger count: {df["passenger_count"].isin([0]).sum()}')
    return df

@task(log_prints=True, retries=3)
def ingest_data(table_name, data):
    # utilizing Sql-connector block to connect postgresql 
    connection_block = SqlAlchemyConnector.load('postgres-connector')
    
    with connection_block.get_connection(begin=False) as engine:
        data.head(n=0).to_sql(name=table_name, con=engine, chunksize=1000, if_exists='replace')
        data.to_sql(name=table_name, con=engine, chunksize=30000, if_exists='append')

@flow(name="Subflow", log_prints=True)
def log_subflow(table_name):
    print(f'Table name: {table_name}')


@flow(name='Ingest Flow')
def main(table_name: str):
    csv_url = 'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2021-01.parquet'
    log_subflow(table_name)
    raw_data = extract_data(csv_url)
    data = transform_data(raw_data)
    ingest_data(table_name, data)


if __name__ == '__main__':
    main('yellow_taxi_trips')
