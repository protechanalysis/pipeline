import requests
import pandas as pd
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

url = "https://randomuser.me/api/"

# Function to make a GET request to the API and fetch data
def get_request():
    response = requests.get(url)
    res = response.json()
    return res

# Function to format the response data into a structured format    
def format_response(**kwargs):
    res = kwargs['ti'].xcom_pull(task_ids='get_request')
    result = res['results'][0]
    return result

# Function to stream data
def stream_data(**kwargs):
    resp = kwargs['ti'].xcom_pull(task_ids='format_response')
    return resp

# Function to transform data
def transform(**kwargs):
    json_data = kwargs['ti'].xcom_pull(task_ids='stream_data')

    data = {
        "first_name": json_data["name"]["first"],
        "last_name": json_data["name"]["last"],
        "title": json_data["name"]["title"],
        "gender": json_data["gender"],
        "address": f'{json_data["location"]["street"]["number"]} {json_data["location"]["street"]["name"]}',
        "city": json_data["location"]["city"],
        "state": json_data["location"]["state"],
        "country": json_data["location"]["country"],
        "postal_code": json_data["location"]["postcode"],
        "timezone": json_data["location"]["timezone"]["offset"],
        "email": json_data["email"],
        "date_of_birth": json_data["dob"]["date"],
        "age": json_data["dob"]["age"],
        "profile_picture": json_data["picture"]["large"],
        "nationality": json_data["nat"]
    }

    df = pd.DataFrame([data])
    return df

# Function to load data to S3
def load_to_s3(**kwargs):
    s3 = S3Hook(aws_conn_id='simple_store')
    bucket_name = 'my-first-terraform-bucket-jeda'
    current_date = datetime.now().strftime('%Y-%m-%d')
    key = f'{current_date}_request.csv'

    ti = kwargs['ti']
    df = ti.xcom_pull(task_ids='transform')

    csv_data = df.to_csv(index=False)
    s3.load_string(string_data=csv_data, key=key, bucket_name=bucket_name, replace=True)

# Default arguments for the DAG
default_args = {
    'owner': 'protectorate',
    'retries': 5,
    'retry_delay': timedelta(minutes=2)
}

# Define the DAG
with DAG(
    dag_id='rand_request',
    default_args=default_args,
    schedule_interval='5 * * * *',
    start_date=datetime(2024, 6, 15),
    catchup=False
) as dag:
    extract_from_url = PythonOperator(
        task_id='get_request',
        python_callable=get_request
    )
    
    format_response_task = PythonOperator(
        task_id='format_response',
        python_callable=format_response,
        provide_context=True
    )
    
    stream_data_task = PythonOperator(
        task_id='stream_data',
        python_callable=stream_data,
        provide_context=True
    )

    transform_task = PythonOperator(
        task_id='transform',
        python_callable=transform,
        provide_context=True
    )

    load_task = PythonOperator(
        task_id='load_to_s3',
        python_callable=load_to_s3,
        provide_context=True
    )

    # Define the task dependencies
    extract_from_url >> format_response_task >> stream_data_task >> transform_task >> load_task
