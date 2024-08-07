"""
module to retrieve and compare heroku env vars from a list of heroku apps
requires that: 1) HEROKU_API_KEY be set, valid and saved in env vars; 2) heroku cli be installed
"""
import logging
import os

import pandas as pd
import requests
from requests import Session

# Constants
CIRCLECI_PERSONAL_API_TOKEN = os.environ.get("CIRCLECI_PERSONAL_API_TOKEN")
CIRCLECI_DEFAULT_APP = "urban-robot"
CURL_CLI_TEST_CMD='''curl -nX GET https://api.heroku.com/apps/urban-robot-dev/config-vars -H "Accept: application/vnd.heroku+json; version=3" -H "Authorization: Bearer $HEROKU_API_KEY"'''

# Set your Heroku API token and app name
HEROKU_API_TOKEN = HEROKU_API_KEY = os.environ.get("HEROKU_API_KEY")  # https://devcenter.heroku.com/articles/platform-api-quickstart
HEROKU_APPS = ["urban-robot-dev", "urban-robot-staging", "urban-robot"]
REQUIRED_ENV_VARS = [
    "AWS_ACCESS_KEY_ID",
    "AWS_DEFAULT_REGION",
    "AWS_SECRET_ACCESS_KEY",
    "API_HOST",
    "CLOUDCONVERT_API_KEY",
    "CURRENT_ENV",
    "FORCE_LOCAL_JOBS",
    "HEROKU_API_KEY",
    "JOB_DEFINITION_ARN",
    "JOB_QUEUE_NAME",
    "MONGODB_ATLAS_CLUSTERNAME",
    "MONGODB_DBNAME",
    "MONGODB_URI",
    "NODE_ENV",
    "NODE_OPTIONS",
    "PORT",
    "REDIS_URL",
    "S3_BUCKET_NAME",
    "SELENIUM_USERID",
    "SELENIUM_PASSWORD",
    "SENDGRID_PASSWORD",
    "SENDGRID_SURFACEOWL_API_KEY",
    "SENDGRID_USERNAME",
    "SURFACE_OWL_API_PREFIX",
    "SURFACE_OWL_API_VERSION",
    "SURFACE_OWL_PYTHON_PATH",
    "SQS_QUEUE_URL",
    "WEB_CONCURRENCY",
    "DAEMON_CONCURRENCY"
]


def get_local_env_vars():
    """pull all local env vars into a dataframe"""
    env_vars_data = {var: os.getenv(var) for var in REQUIRED_ENV_VARS}
    # Convert the dictionary to a pandas DataFrame
    df_env_vars = pd.DataFrame.from_dict(env_vars_data, orient='index', columns=['local']).sort_index()
    return df_env_vars, env_vars_data


def get_heroku_env_vars(app_name="urban-robot-dev"):
    """
    Retrieves heroku env vars from a single heroku app
    :param app_name: string
    :return: pandas data frame with heroku env vars, and json with heroku env vars
    """
    app_name = str(app_name)
    url = f"https://api.heroku.com/apps/{app_name}/config-vars"

    # request will fail without an API token in env vars
    assert HEROKU_API_TOKEN is not None, "HEROKU_API_KEY environment variable is not set"
    # Set headers for Heroku API
    headers = {
        "Authorization": f"Bearer {HEROKU_API_TOKEN.strip()}",
        "Accept": "application/vnd.heroku+json; version=3",
    }

    with Session() as session:
        print("check raw HTTP request before it is sent")
        request = requests.Request('GET', url, headers=headers).prepare()  # Create a prepared request object
        response = session.send(request)
        print(request.headers)
        print("\n")

        # Make the API request
        logging.warning(f"url: {url}")
        # response = requests.get(url, headers=headers)
        logging.warning("check request headers")
        logging.warning(response.request.headers)

        # Check if the request was successful & return result
        config_vars = response.json()
        if response.status_code == 200:
            df = pd.DataFrame.from_dict(config_vars, orient="index", columns=[app_name])
            return df, config_vars
        elif response.status_code == 401 and response.json()["id"] == "unauthorized":
            logging.error(f"ERROR: {response.status_code} - {config_vars["id"]}: {config_vars["message"]}")
            logging.error(f"{CURL_CLI_TEST_CMD}\n")
        else:
            logging.error("ERROR: Failed to retrieve config vars:", response.status_code, config_vars)

        return None, None


def get_circleci_env_vars_keys(circleci_app_name=CIRCLECI_DEFAULT_APP):
    """Fetches and returns environment variables from a CircleCI project using the requests module."""
    CIRCLECI_PROJECT_SLUG = f"gh/surfaceowl-ai/{circleci_app_name}"
    CIRCLECI_API_URL = f"https://circleci.com/api/v2/project/{CIRCLECI_PROJECT_SLUG}/envvar"
    headers = {
        "Circle-Token": CIRCLECI_PERSONAL_API_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        return get_circleci_env_vars_keys_values_to_df(CIRCLECI_API_URL, headers)
    except requests.RequestException as e:
        logging.error(f"An error occurred: {e}")
        return None, None


# TODO Rename this here and in `get_circleci_env_vars`
def get_circleci_env_vars_keys_values_to_df(CIRCLECI_API_URL, headers):
    response = requests.get(CIRCLECI_API_URL, headers=headers)
    response.raise_for_status()  # Check for HTTP request errors
    payload_data = response.json().get('items', [])

    df_circleci = pd.DataFrame(payload_data).fillna("not_set")
    df_circleci.set_index('name', inplace=True)
    df_circleci.columns = [f'CIRCLECI_{col}' for col in df_circleci.columns]
    df_circleci = df_circleci[["CIRCLECI_created_at", "CIRCLECI_value"]]

    logging.info(df_circleci)
    return df_circleci, payload_data  # Return DataFrame and raw data


def get_all_vars_into_matrix(heroku_app_targets=HEROKU_APPS):
    """
    Loops through Heroku app names, retrieves environment variables,
    concatenates them into a single DataFrame, and replaces NaNs with "not_set".

    Args:
        heroku_app_targets (list, optional): List of Heroku app names. Defaults to HEROKU_APPS.

    Returns:
        pd.DataFrame: DataFrame containing all environment variables for each app.
    """
    # first column is our required env vars
    df_required = pd.DataFrame(index=REQUIRED_ENV_VARS, columns=["REQUIRED_ENV_VARS"])
    df_required["REQUIRED_ENV_VARS"] = "Yes"
    all_dataframes = [df_required]
    # second col is env vars in our local environment
    df_local, _ = get_local_env_vars()
    all_dataframes.append(df_local)

    df_circleci, _ = get_circleci_env_vars_keys("urban-robot")
    all_dataframes.append(df_circleci)

    # get Heroku env vars
    for app_name in heroku_app_targets:
        # Get DataFrame for the current app (assuming get_heroku_env_vars exists)
        df_app_vars, _ = get_heroku_env_vars(app_name)

        if df_app_vars is not None:
            # Handle missing values (replace NaN with "not_set")
            # df_app_vars = df_app_vars.fillna("not_set")
            # Append the DataFrame to the list
            all_dataframes.append(df_app_vars)

        else:
            print(f"ERROR: for Heroku app name: {app_name}.  Check Heroku API login credentials.\n")
    df_final = pd.concat(all_dataframes, axis=1).fillna("not_set")
    return df_final.groupby('REQUIRED_ENV_VARS', group_keys=False).apply(lambda x: x.sort_index(), include_groups=False)



if __name__ == "__main__":
    df_final = get_all_vars_into_matrix()

    print(df_final)


