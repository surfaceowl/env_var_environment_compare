"""
module to retrieve and compare heroku env vars from a list of heroku apps
requires that: 1) HEROKU_API_KEY be set, valid and saved in env vars; 2) heroku cli be installed
"""
import os

import pandas as pd
import requests

# Constants
CIRCLECI_PERSONAL_API_TOKEN = os.environ.get("CIRCLECI_PERSONAL_API_TOKEN")
CIRCLECI_DEFAULT_APP = "urban-robot"


# Set your Heroku API token and app name
HEROKU_API_TOKEN = os.environ.get("HEROKU_API_TOKEN")
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
    "SQS_QUEUE_URL",
    "WEB_CONCURRENCY",
    "DAEMON_CONCURRENCY"
]


def get_heroku_env_vars(app_name="urban-robot-dev"):
    """
    Retrieves heroku env vars from a single heroku app
    :param app_name: string
    :return: pandas data frame with heroku env vars, and json with heroku env vars
    """
    app_name = str(app_name)
    url = f"https://api.heroku.com/apps/{app_name}/config-vars"

    # Set headers for Heroku API
    headers = {
        "Authorization": f"Bearer {HEROKU_API_TOKEN}",
        "Accept": "application/vnd.heroku+json; version=3",
    }

    # Make the API request
    response = requests.get(url, headers=headers)

    # Check if the request was successful & return result
    if response.status_code == 200:
        config_vars = response.json()
        print(config_vars)
        df = pd.DataFrame.from_dict(config_vars, orient="index", columns=[app_name])
        return df, config_vars
    else:
        print("Failed to retrieve config vars:", response.status_code)
        return None, None


def get_circleci_env_vars(circleci_app_name=CIRCLECI_DEFAULT_APP):
    """Fetches and returns environment variables from a CircleCI project using the requests module."""
    CIRCLECI_PROJECT_SLUG = f"gh/surfaceowl-ai/{circleci_app_name}"
    CIRCLECI_API_URL = f"https://circleci.com/api/v2/project/{CIRCLECI_PROJECT_SLUG}/envvar"
    headers = {
        "Circle-Token": CIRCLECI_PERSONAL_API_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.get(CIRCLECI_API_URL, headers=headers)
        response.raise_for_status()  # Check for HTTP request errors
        payload_data = response.json().get('items', [])

        df_circleci = pd.DataFrame(payload_data).fillna("not_set")
        df_circleci.set_index('name', inplace=True)
        df_circleci.columns = [f'CIRCLECI_{col}' for col in df_circleci.columns]
        df_circleci = df_circleci[["CIRCLECI_created_at", "CIRCLECI_value"]]

        print(df_circleci)
        return df_circleci, payload_data  # Return DataFrame and raw data

    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None, None


def get_all_vars_in_matrix(heroku_app_targets=HEROKU_APPS):
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
    # Initialize a list to store DataFrames
    all_dataframes = [df_required]

    df_circleci, _ = get_circleci_env_vars("urban-robot")
    all_dataframes.append(df_circleci)

    # get Heroku env vars
    for app_name in heroku_app_targets:
        # Get DataFrame for the current app (assuming get_heroku_env_vars exists)
        df_app_vars, _ = get_heroku_env_vars(app_name)

        # Handle missing values (replace NaN with "not_set")
        df_app_vars = df_app_vars.fillna("not_set")

        # Append the DataFrame to the list
        all_dataframes.append(df_app_vars)

    return pd.concat(all_dataframes, axis=1).fillna("not_set").sort_index()


if __name__ == "__main__":
    df_final = get_all_vars_in_matrix()
    print(df_final)
    # df_ci = get_circleci_env_vars()
    # print(df_ci)

