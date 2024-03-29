import vanna as vn
import requests
import sys
import io
import pandas as pd
import contextlib
import stat
import os
import pytest
from vanna.exceptions import ValidationError, ImproperlyConfigured

endpoint_base = os.environ.get('VANNA_ENDPOINT', 'https://debug.vanna.ai')

vn._endpoint = endpoint_base + '/rpc'
vn._unauthenticated_endpoint = endpoint_base + '/unauthenticated_rpc'

## Helper functions
def switch_to_user(user, monkeypatch):
    monkeypatch.setattr(sys, 'stdin', io.StringIO('DEBUG\n'))

    api_key = vn.get_api_key(email=f'{user}@example.com')
    vn.set_api_key(api_key)

## Tests

def test_debug_env():
    # Get endpoint_base + '/reset'
    r = requests.get(endpoint_base + '/reset')
    assert r.status_code == 200
    assert r.text == 'Database reset'

def test_create_user1(monkeypatch):
    monkeypatch.setattr(sys, 'stdin', io.StringIO('DEBUG\n'))

    api_key = vn.get_api_key(email='user1@example.com')
    vn.set_api_key(api_key)

    models = vn.get_models()

    assert models == ['demo-tpc-h']


@pytest.mark.parametrize("model_name", ["Test @Org_"])
def test_create_model(model_name):
    rv = vn.create_model(model=model_name, db_type='Snowflake')
    assert rv == True

    models = vn.get_models()
    assert 'test-org' in models


def test_is_user1_in_model():
    rv = vn.get_models()
    assert rv == ['demo-tpc-h', 'test-org']


def test_is_user2_in_model(monkeypatch):
    switch_to_user('user2', monkeypatch)

    models = vn.get_models()

    assert models == ['demo-tpc-h']

def test_switch_back_to_user1(monkeypatch):
    switch_to_user('user1', monkeypatch)

    models = vn.get_models()
    assert models == ['demo-tpc-h', 'test-org']

def test_set_model_my_model():
    with pytest.raises(ValidationError):
        vn.set_model('my-model')

def test_set_model():
    vn.set_model('test-org')
    assert vn.__org == 'test-org' # type: ignore

def test_add_user_to_model(monkeypatch):
    rv = vn.add_user_to_model(model='test-org', email="user2@example.com", is_admin=False)
    assert rv == True

    switch_to_user('user2', monkeypatch)
    models = vn.get_models()
    assert models == ['demo-tpc-h', 'test-org']

def test_update_model_visibility(monkeypatch):
    rv = vn.update_model_visibility(public=True)
    # user2 is not an admin, so this should fail
    assert rv == False

    switch_to_user('user1', monkeypatch)
    rv = vn.update_model_visibility(public=True)

    switch_to_user('user3', monkeypatch)
    models = vn.get_models()
    assert models == ['demo-tpc-h', 'test-org']

    switch_to_user('user1', monkeypatch)

    rv = vn.update_model_visibility(public=False)
    assert rv == True

    switch_to_user('user3', monkeypatch)

    models = vn.get_models()
    assert models == ['demo-tpc-h']

def test_generate_explanation(monkeypatch):
    switch_to_user('user1', monkeypatch)
    rv = vn.generate_explanation(sql="SELECT * FROM students WHERE name = 'John Doe'")
    assert rv == 'AI Response'

def test_generate_question():
    rv = vn.generate_question(sql="SELECT * FROM students WHERE name = 'John Doe'")
    assert rv == 'AI Response'

def test_generate_sql():
    rv = vn.generate_sql(question="Who are the top 10 customers by Sales?")
    assert rv == 'No SELECT statement could be found in the SQL code'

def test_generate_plotly():
    data = {
    'Name': ['John', 'Emma', 'Tom', 'Emily', 'Alex'],
    'Age': [25, 28, 22, 31, 24],
    'Country': ['USA', 'Canada', 'UK', 'Australia', 'USA'],
    'Salary': [50000, 60000, 45000, 70000, 55000]
    }

    # Create a dataframe from the dictionary
    df = pd.DataFrame(data)

    rv = vn.generate_plotly_code(question="Who are the top 10 customers by Sales?", sql="SELECT * FROM students WHERE name = 'John Doe'", df=df)
    assert rv == 'AI Response'

def test_generate_questions():
    rv = vn.generate_questions()
    assert rv == ['AI Response']

def test_generate_followup_questions():
    data = {
    'Name': ['John', 'Emma', 'Tom', 'Emily', 'Alex'],
    'Age': [25, 28, 22, 31, 24],
    'Country': ['USA', 'Canada', 'UK', 'Australia', 'USA'],
    'Salary': [50000, 60000, 45000, 70000, 55000]
    }

    # Create a dataframe from the dictionary
    df = pd.DataFrame(data)

    questions = vn.generate_followup_questions(question="Who are the top 10 customers by Sales?", df=df)

    assert questions == ['AI Response']

def test_add_sql():
    rv = vn.add_sql(question="What's the data about student John Doe?", sql="SELECT * FROM students WHERE name = 'John Doe'")
    assert rv == True

    rv = vn.add_sql(question="What's the data about student Jane Doe?", sql="SELECT * FROM students WHERE name = 'Jane Doe'")
    assert rv == True

def test_generate_sql_caching():
    rv = vn.generate_sql(question="What's the data about student John Doe?")

    assert rv == 'SELECT * FROM students WHERE name = \'John Doe\''

def test_remove_sql():
    rv = vn.remove_sql(question="What's the data about student John Doe?")
    assert rv == True

def test_flag_sql():
    rv = vn.flag_sql_for_review(question="What's the data about student Jane Doe?")
    assert rv == True

def test_get_all_questions():
    rv = vn.get_all_questions()
    assert rv.shape == (3, 5)

    vn.set_model('demo-tpc-h')
    rv = vn.get_all_questions()
    assert rv.shape == (0, 0)

# def test_get_accuracy_stats():
#     rv = vn.get_accuracy_stats()
#     assert rv == AccuracyStats(num_questions=2, data={'No SQL Generated': 2, 'SQL Unable to Run': 0, 'Assumed Correct': 0, 'Flagged for Review': 0, 'Reviewed and Approved': 0, 'Reviewed and Rejected': 0, 'Reviewed and Updated': 0})

def test_add_documentation_fail():
    rv = vn.add_documentation(documentation="This is the documentation")
    assert rv == False

def test_add_ddl_pass_fail():
    rv = vn.add_ddl(ddl="This is the ddl")
    assert rv == False

def test_add_sql_pass_fail():
    rv = vn.add_sql(question="How many students are there?", sql="SELECT * FROM students")
    assert rv == False

def test_add_documentation_pass(monkeypatch):
    switch_to_user('user1', monkeypatch)
    vn.set_model('test-org')
    rv = vn.add_documentation(documentation="This is the documentation")
    assert rv == True

def test_add_ddl_pass():
    rv = vn.add_ddl(ddl="This is the ddl")
    assert rv == True

def test_add_sql_pass():
    rv = vn.add_sql(question="How many students are there?", sql="SELECT * FROM students")
    assert rv == True

num_training_data = 4

def test_get_training_data():
    rv = vn.get_training_data()
    assert rv.shape == (num_training_data, 4)

def test_remove_training_data():
    training_data = vn.get_training_data()

    for index, row in training_data.iterrows():
        rv = vn.remove_training_data(row['id'])
        assert rv == True

        assert vn.get_training_data().shape[0] == num_training_data-1-index

def test_create_model_and_add_user():
    created = vn.create_model('test-org2', 'Snowflake')
    assert created == True

    added = vn.add_user_to_model(model='test-org2', email="user5@example.com", is_admin=False)
    assert added == True

def test_ask_no_output():
    vn.run_sql = lambda sql: pd.DataFrame({'Name': ['John', 'Emma', 'Tom', 'Emily', 'Alex']})
    vn.generate_sql = lambda question: 'SELECT * FROM students'
    vn.ask(question="How many students are there?")

def test_ask_with_output():
    sql, df, fig, followup_questions = vn.ask(question="How many students are there?", print_results=False)

    assert sql == 'SELECT * FROM students'

    assert df.to_csv() == ',Name\n0,John\n1,Emma\n2,Tom\n3,Emily\n4,Alex\n'

def test_generate_meta():
    meta = vn.generate_meta("What tables are available?")

    assert meta == 'AI Response'

def test_double_train():
    vn.set_model('test-org')

    training_data = vn.get_training_data()
    assert training_data.shape == (0, 0)

    trained = vn.train(question="What's the data about student John Doe?", sql="SELECT * FROM students WHERE name = 'John Doe'")
    assert trained == True

    training_data = vn.get_training_data()
    assert training_data.shape == (1, 4)

    vn.train(question="What's the data about student John Doe?", sql="SELECT * FROM students WHERE name = 'John Doe'")

    training_data = vn.get_training_data()
    assert training_data.shape == (1, 4)

def test_get_related_training_data():
    data = vn.get_related_training_data(question="What's the data about student John Doe?")
    assert data.questions[0]['question'] == 'What is the total sales for each product?'
    assert data.questions[0]['sql'] == 'SELECT * FROM ...'
    assert data.ddl == ['DDL here']
    assert data.documentation == ['Documentation here']

@pytest.mark.parametrize("params", [
    dict(
        question=None,
        sql="SELECT * FROM students WHERE name = 'Jane Doe'",
        documentation=False,
        ddl=None,
        sql_file=None,
        json_file=None,
    ),
    dict(
        question=None,
        sql="SELECT * FROM students WHERE name = 'Jane Doe'",
        documentation=True,
        ddl=None,
        sql_file=None,
        json_file=None,
    ),
    dict(
        question=None,
        sql=None,
        documentation=False,
        ddl="This is the ddl",
        sql_file=None,
        json_file=None,
    ),
    dict(
        question=None,
        sql=None,
        documentation=False,
        ddl=None,
        sql_file="tests/fixtures/sql/testSqlSelect.sql",
        json_file=None,
    ),
    dict(
        question=None,
        sql=None,
        documentation=False,
        ddl=None,
        sql_file=None,
        json_file="tests/fixtures/questions.json"
    ),
    dict(
        question=None,
        sql=None,
        documentation=False,
        ddl=None,
        sql_file="tests/fixtures/sql/testSqlCreate.sql",
        json_file=None,
    ),
])
def test_train_success(monkeypatch, params):
    vn.set_model('test-org')
    assert vn.train(**params)


@pytest.mark.parametrize("params, expected_exc_class", [
    (
        dict(
            question="What's the data about student John Doe?",
            sql=None,
            documentation=False,
            ddl=None,
            sql_file=None,
            json_file=None,
        ),
        ValidationError
    ),
    (
        dict(
            question=None,
            sql=None,
            documentation=False,
            ddl=None,
            sql_file="wrong/path/or/file.sql",
            json_file=None,
        ),
        ImproperlyConfigured
    ),
    (
        dict(
            question=None,
            sql=None,
            documentation=False,
            ddl=None,
            sql_file=None,
            json_file="wrong/path/or/file.json",
        ),
        ImproperlyConfigured
    )
])
def test_train_validations(monkeypatch, params, expected_exc_class):
    vn.set_model('test-org')

    with pytest.raises((ValidationError, ImproperlyConfigured)) as exc:
        vn.train(**params)
        assert isinstance(exc, expected_exc_class)


@pytest.mark.parametrize('model_name', [1234, ['test_org']])
def test_set_model_validation(model_name):
    # test invalid model name
    with pytest.raises(ValidationError) as exc:
        vn.set_model(model_name)
        assert "Please provide model name in string format" in exc.args[0]


def mock_connector(host, dbname, user, password, port):
    pass


@pytest.mark.parametrize('params, none_param', [
    (
        dict(
            host=None,
            dbname="test-db",
            user="test-user",
            password="test-password",
            port=5432
        ),
        "host"
    ),
    (
        dict(
            host="localhost",
            dbname=None,
            user="test-user",
            password="test-password",
            port=5432,
        ),
        "database"
    ),
    (
        dict(
            host="localhost",
            dbname="test-db",
            user=None,
            password="test-password",
            port=5432,
        ),
        "user"
    ),
    (
        dict(
            host="localhost",
            dbname="test-db",
            user="test-user",
            password=None,
            port=5432,
        ),
        "password",
    ),
    (
        dict(
            host="localhost",
            dbname="test-db",
            user="test-user",
            password="test-password",
            port=None,
        ),
        "port"
    ),
])
def test_connect_to_postgres_validations(monkeypatch, params, none_param):
    monkeypatch.setattr("psycopg2.connect", mock_connector)
    with pytest.raises(ImproperlyConfigured) as exc:
        vn.connect_to_postgres(**params)
        assert f"Please set your postgres {none_param}" in exc.args[0]


class Client:
    def query(self, query):

        pass


@pytest.mark.parametrize("params", [
    dict(project_id=None),
])
def test_connect_to_bigquery_validations(monkeypatch, params):
    monkeypatch.setattr("google.cloud.bigquery.Client", Client)
    with pytest.raises(ImproperlyConfigured) as exc:
        vn.connect_to_bigquery(**params)
        assert "Please set your Google Cloud Project ID." in exc.args[0]


@pytest.mark.parametrize("params, expected_err", [
    (
        dict(
            project_id="test-project",
            cred_file_path="wrong/file/path.json"
        ),
        "No such configuration file: wrong/file/path.json"
    ),
    (
        dict(
            project_id="test-project",
            cred_file_path="tests"
        ),
        "Config should be a file: tests"
    )
])
def test_connect_to_bigquery_creds_path_validations(monkeypatch, params, expected_err):
    monkeypatch.setattr("google.cloud.bigquery.Client", Client)
    with pytest.raises(ImproperlyConfigured) as exc:
        vn.connect_to_bigquery(**params)
        assert expected_err in exc.args[0]


@pytest.mark.parametrize("params", [
    dict(
        project_id="test-project",
        cred_file_path="tests/test-creds.json"
    ),
])
def test_connect_to_bigquery_creds_file_permissions(monkeypatch, params):
    monkeypatch.setattr("google.cloud.bigquery.Client", Client)
    with create_file(params["cred_file_path"]) as creds_path:
        with pytest.raises(ImproperlyConfigured) as exc:
            vn.connect_to_bigquery(**params)
            assert f"Cannot read the config file. Please grant read privileges: {creds_path}" in exc.args[0]


@contextlib.contextmanager
def create_file(file_path):
    with open(file_path, "w") as f:
        pass
    os.chmod(file_path, stat.S_IWUSR)
    try:
        yield file_path
    finally:
        os.remove(file_path)
