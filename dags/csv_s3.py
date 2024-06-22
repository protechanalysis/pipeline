import pandas as pd
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

# Function to load CSV file and push the DataFrame to XCom
def load_csv(**kwargs):
    # Read the first 50 rows of the CSV file into a DataFrame
    df = pd.read_csv('/opt/airflow/dags/british_air_sentiments.csv', nrows=50)
    
    # Push DataFrame to XCom
    kwargs['ti'].xcom_push(key='csv_data', value=df.to_dict())

# Function to load DataFrame from XCom and upload it to S3
def load_to_s3(**kwargs):
    # Initialize S3 hook with connection ID
    s3 = S3Hook(aws_conn_id='simple_store')
    
    # Define S3 bucket name and file key
    bucket_name = 'my-first-terraform-bucket-jeda'
    key = 'british_air_review.csv'

    # Retrieve the DataFrame dictionary from XCom
    ti = kwargs['ti']
    df_dict = ti.xcom_pull(task_ids='load_csv', key='csv_data')
    
    # Convert dictionary back to DataFrame
    df = pd.DataFrame(df_dict)

    # Convert DataFrame to CSV string
    csv_data = df.to_csv(index=False)
    
    # Upload the CSV string to S3
    s3.load_string(string_data=csv_data, key=key, bucket_name=bucket_name, replace=True)

# Default arguments for the DAG
default_args = {
    'owner': 'protectorate',             # Owner of the DAG
    'retries': 5,                        # Number of retries in case of failure
    'retry_delay': timedelta(minutes=2)  # Delay between retries
}

# Define the DAG
with DAG(
    dag_id='csv_ingest_s3',               # Unique identifier for the DAG
    default_args=default_args,            # Default arguments for the DAG
    schedule_interval='@daily',           # Schedule interval for the DAG
    start_date=datetime(2024, 6, 22),     # Start date for the DAG
    catchup=False                         # Whether to catch up on missed runs
) as dag:
    
    # Define the PythonOperator to execute the load_csv function
    extract_local_csv = PythonOperator(
        task_id='load_csv',               # Unique identifier for the task
        python_callable=load_csv,         # Function to be called
        provide_context=True,             # Provide context to the function (for XCom)
        dag=dag
    )

    # Define the PythonOperator to execute the load_to_s3 function
    load_to_s3 = PythonOperator(
        task_id='load_to_s3',             # Unique identifier for the task
        python_callable=load_to_s3,       # Function to be called
        provide_context=True,             # Provide context to the function (for XCom)
        dag=dag
    )

    # Set the task dependency
    extract_local_csv >> load_to_s3       # Ensure load_to_s3 runs after extract_local_csv
