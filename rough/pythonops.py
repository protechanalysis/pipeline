from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'protectorate',
    'retries': 5,
    'retry_delay': timedelta(minutes=2)
}

def greet():
    print("Hello Adewunmi!!!, welcome to airflow with python operator")

def greetings():
    print("Hello Adewunmi!!!, welcome to airflow with python operator task 2")


with DAG(
    dag_id='first_python_operator',
    default_args=default_args,
    description='this is my first dag',
    start_date=datetime(2024, 5, 25, 2),
    schedule_interval='@daily'
) as dag:
    task1 = PythonOperator(
        task_id='greet',
        python_callable=greet
    )

    task2 = PythonOperator(
        task_id='greet_task2',
        python_callable=greetings
    )

    task1 >> task2