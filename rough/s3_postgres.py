import requests
import pandas as pd
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.hooks.postgres_hook import PostgresHook

# Define constants
url = "https://randomuser.me/api/"
POSTGRES_CONN_ID = 'post_s3'  # Update with your PostgreSQL connection ID

# Function to make a GET request to the API and fetch data
def fetch_request():
    response = requests.get(url)
    res = response.json()
    result = res['results'][0]
    return result

# Function to transform data
def transform(**kwargs):
    ti = kwargs['ti']
    json_data = ti.xcom_pull(task_ids='fetch_user')
    
    data = {
        "id": json_data["login"]["uuid"],
        "first_name": json_data["name"]["first"],
        "last_name": json_data["name"]["last"],
        "gender": json_data["gender"],
        "state": json_data["location"]["state"],
        "country": json_data["location"]["country"],
        "email": json_data["email"],
        "date_of_birth": json_data["dob"]["date"],
        "age": json_data["dob"]["age"],
        "profile_picture": json_data["picture"]["large"],
        "nationality": json_data["nat"]
    }
    
    return data

# Function to load data into PostgreSQL
def load_to_postgres(**kwargs):
    ti = kwargs['ti']
    transformed_data = ti.xcom_pull(task_ids='transform')
    
    pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
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
        age INTEGER,
        profile_picture VARCHAR(255),
        nationality VARCHAR(5)
    );
    """
    
    insert_query = """
    INSERT INTO random_users_data (id, first_name, last_name, gender, state, country, email, date_of_birth, age, profile_picture, nationality)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    
    try:
        cursor.execute(create_table_query)
        cursor.execute(insert_query, (
            transformed_data["id"],
            transformed_data["first_name"],
            transformed_data["last_name"],
            transformed_data["gender"],
            transformed_data["state"],
            transformed_data["country"],
            transformed_data["email"],
            transformed_data["date_of_birth"],
            transformed_data["age"],
            transformed_data["profile_picture"],
            transformed_data["nationality"]
        ))
        pg_conn.commit()
    except Exception as e:
        pg_conn.rollback()
        raise e
    finally:
        cursor.close()
        pg_conn.close()

# Function to load data from PostgreSQL to S3
def load_postgres_to_s3():
    pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    pg_conn = pg_hook.get_conn()
    cursor = pg_conn.cursor()

    query = "SELECT * FROM random_users_data"
    cursor.execute(query)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    
    df = pd.DataFrame(rows, columns=columns)
    s3 = S3Hook(aws_conn_id='simple_store')  # Update with your S3 connection ID
    bucket_name = 'my-first-terraform-bucket-jeda'
    key = 'random_user_data.csv'
    csv_data = df.to_csv(index=False)
    s3.load_string(string_data=csv_data, key=key, bucket_name=bucket_name, replace=True)

    cursor.close()
    pg_conn.close()

# Default arguments
default_args = {
    'owner': 'protectorate',
    'depends_on_past': False,
    'start_date': datetime(2024, 6, 16),
    'email': 'protectorateog@gmail.com',
    'email_on_failure': True,
    'email_on_retry': True,
    'retries': 5,
    'retry_delay': timedelta(minutes=2)
}

# Define DAG
with DAG(
    dag_id='random_user_request_data',
    default_args=default_args,
    description='A simple ETL DAG that fetches a random user, transforms data, and loads it to PostgreSQL and S3'
    #schedule_interval='@weekly',
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

    load_to_s3 = PythonOperator(
        task_id='load_to_s3',
        python_callable=load_postgres_to_s3,
        dag=dag,
    )

    # Define task dependencies
    fetch_user >> transform_data >> load_to_postgres >> load_to_s3
