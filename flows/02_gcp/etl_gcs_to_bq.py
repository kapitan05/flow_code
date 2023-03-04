from pathlib import Path
import pandas as pd
from prefect import flow, task, get_run_logger
from prefect_gcp.cloud_storage import GcsBucket
from prefect_gcp import GcpCredentials


@task(retries=3)
def extract_from_gcs(color: str, year: int, month: int) -> Path:
    """Download trip data from GCS"""
    gcs_path = f'data/{color}/{color}_tripdata_{year}-{month:02}.parquet'
    gcs_block = GcsBucket.load('zoom-gcs')
    gcs_block.download_object_to_path(gcs_path, gcs_path)
    return gcs_path   

@task()
def transform(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    logger = get_run_logger()
    logger.info(f'Number of rows {df.shape[0]}')
    print(f"pre missing pass count: {df['passenger_count'].isna().sum()}")
    #df['passenger_count'].fillna(0, inplace=True)
    print(f"post missing pass count: {df['passenger_count'].isna().sum()}")
    return df

@task()
def write_bq(df: pd.DataFrame) -> None:
    """Write data ro BQ"""

    gcp_credentials_block = GcpCredentials.load("zoom-gcp-creds")

    df.to_gbq(
        destination_table='dezoomcamp.rides',
        project_id='zmcamp-de-378312',
        credentials=gcp_credentials_block.get_credentials_from_service_account(),
        chunksize=100_000,
        if_exists='append'
    )

@flow()
def etl_gcs_to_bq(color: str, month: int, year: int):
    """Main ETL flow to load data into BQ"""
    path = extract_from_gcs(color, year, month)
    df = transform(path)

    write_bq(df)
    return len(df)

@flow()
def parent_flow(color: str, months: list[int], year: int) -> None:
    total_rows = 0
    for month in months:
        total_rows += etl_gcs_to_bq(color, month, year)
    print(total_rows)

if __name__ == "__main__":
    color = 'green'
    months = [2, 3]
    year = 2019
    parent_flow(color, months, year)