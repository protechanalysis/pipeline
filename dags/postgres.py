import requests
import pandas as pd
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.hooks.postgres_hook import PostgresHook




url = "https://randomuser.me/api/"

# Function to make a GET request to the API and fetch data
def fetch_request():
    response = requests.get(url)
    res = response.json()
    result = res['results'][0]
    return result

def transform(**kwargs):
    json_data = kwargs['ti'].xcom_pull(task_ids='fetch_user')

    data = {
        "first_name": str(json_data["name"]["first"]),
        "last_name": str(json_data["name"]["last"]),
        "gender": str(json_data["gender"]),
        "state": str(json_data["location"]["state"]),
        "country": str(json_data["location"]["country"]),
        "email": str(json_data["email"]),
        "id": str(json_data["login"]["uuid"]),
        "date_of_birth": str(json_data["dob"]["date"]),
        "age": str(json_data["dob"]["age"]),  # Keep age as string for easy schema in postgres
        "profile_picture": str(json_data["picture"]["large"]),
        "nationality": str(json_data["nat"])
    }


    df = pd.DataFrame([data])
    return df


def load_to_postgres(**kwargs):
    ti = kwargs['ti']
    user_data = ti.xcom_pull(task_ids='transform').iloc[0]  # Extract the first row of the DataFrame
    #.iloc[0] is necessary to extract the single row from the DataFrame as a dictionary-like object
    
    pg_hook = PostgresHook(postgres_conn_id='post_s3')
    pg_conn = pg_hook.get_conn()
    cursor = pg_conn.cursor()
    
    create_table_query = """
    CREATE TABLE IF NOT EXISTS random_users_data (
        id VARCHAR(50) PRIMARY KEY,
        first_name VARCHAR(50),
        last_name VARCHAR(50),
        gender VARCHAR(10),
        state VARCHAR(50),
        country VARCHAR(50),
        email VARCHAR(100) UNIQUE,
        date_of_birth TIMESTAMPTZ,
        age integer,
        profile_picture VARCHAR(255),
        nationality VARCHAR(5)
    );
    """
    
    insert_query = """
    INSERT INTO random_users_data (id, first_name, last_name, gender, state, country, email, date_of_birth, age, profile_picture, nationality)
    VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    
    cursor.execute(create_table_query)
    cursor.execute(insert_query, (
        user_data["id"], user_data["first_name"], user_data["last_name"], 
        user_data["gender"], user_data["state"], user_data["country"], 
        user_data["email"], user_data["date_of_birth"], user_data["age"], 
        user_data["profile_picture"], user_data["nationality"]
    ))
    pg_conn.commit()
    cursor.close()
    pg_conn.close()

default_args = {
    'owner': 'protectorate',
    'depends_on_past': False,
    'start_date': datetime(2024, 6, 17),
    'email': 'protectorateog@gmail.com',
    'email_on_failure': True,
    'email_on_retry': True,
    'retries': 5,
    'retry_delay': timedelta(minutes=2)
}

# Define DAG
with DAG(
    dag_id='postgres',
    default_args=default_args,
    description='A simple ETL DAG that fetches a random user, transforms data, and loads it to PostgreSQL',
    schedule_interval='@daily',
) as dag:

    # Define tasks
    fetch_user = PythonOperator(
        task_id='fetch_user',
        python_callable=fetch_request,
        dag=dag,
    )

    transform_data = PythonOperator(
        task_id='transform',
        python_callable=transform,
        provide_context=True,
        dag=dag,
    )

    load_to_postgres = PythonOperator(
        task_id='load_to_postgres',
        python_callable=load_to_postgres,
        provide_context=True,
        dag=dag,
    )

    # Task dependencies
    fetch_user >> transform_data >> load_to_postgres