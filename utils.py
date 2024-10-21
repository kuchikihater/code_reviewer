from urllib.parse import urlparse

import requests

from logger_setup import logger


def parse_github_pull_request_url(url: str) -> tuple[str, str, str]:
    """
    Parses a GitHub pull request URL to extract the owner, repository name, and pull request number.

    Args:
        url (str): The URL of the GitHub pull request.

    Returns:
        tuple: A tuple containing the repository owner (owner), repository name (repo),
               and the pull request number (pull_number).

    Raises:
        ValueError: If the URL format is invalid or the necessary parts cannot be extracted.
    """
    try:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')

        owner = path_parts[0]
        repo = path_parts[1]
        if path_parts[2] != 'pull':
            logger.error('Invalid GitHub pull request URL format.')
            raise ValueError('Invalid GitHub pull request URL format.')

        pull_number = path_parts[3]
        return owner, repo, pull_number

    except (IndexError, ValueError) as e:
        logger.error(f'Error parsing URL: {e}')
        raise ValueError('Invalid GitHub pull request URL.') from e


def make_github_api_request(api_url, headers):
    """
    Makes a GET request to the GitHub API and handles possible errors.

    Args:
        api_url (str): The URL for the request to the GitHub API.
        headers (dict): The headers for the request, including the authorization token.

    Returns:
        dict: The response data if the request is successful.

    Raises:
        Exception: If an error occurs corresponding to the processed status code.
"""
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 403:
            logger.error('GitHub API rate limit exceeded.')
            raise Exception('GitHub API rate limit exceeded.') from e
        elif status_code == 404:
            logger.error('Pull request not found.')
            raise Exception('Pull request not found.') from e
        else:
            logger.error(f'HTTP error occurred: {e}')
            raise
    except requests.exceptions.RequestException as e:
        logger.error(f'HTTP request failed: {e}')
        raise