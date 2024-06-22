import pandas as pd
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator

def load_csv(**kwargs):
    # Read the CSV file
    df = pd.read_csv('/opt/airflow/dags/british_air_sentiments.csv', nrows=50)
    
    # Print the first 5 rows
    print(df.head(5))
    
    # Optionally push DataFrame to XCom
    # kwargs['ti'].xcom_push(key='csv_data', value=df.to_dict())

default_args = {
    'owner': 'protectorate',
    'retries': 5,
    'retry_delay': timedelta(minutes=2)
}

# Define the DAG
with DAG(
    dag_id='load_csv_dag',
    default_args=default_args,
    schedule_interval='@daily',
    start_date=datetime(2024, 6, 22),
    catchup=False
) as dag:
    
    extract_from_local = PythonOperator(
        task_id='load_csv',
        python_callable=load_csv
        #provide_context=True  # Ensure context is provided for XCom
    )

    extract_from_local
