from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'protectorate',
    'retries': 5,
    'retry_delay': timedelta(minutes=2)
}

with DAG(
    dag_id='my_first_dag2',
    default_args=default_args,
    description='this is my first dag',
    start_date=datetime(2024, 5, 25, 2),
    schedule_interval='@daily'
) as dag:
    task1 = BashOperator(
        task_id='first_task',
        bash_command="echo hello world, this is the first task"
    )

    task2 = BashOperator(
        task_id='first_task_0v2',
        bash_command="echo hello world, this is the second task"
    )

    task1 >> task2