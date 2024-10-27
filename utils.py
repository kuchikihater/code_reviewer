from urllib.parse import urlparse

import requests

from logger_setup import logger

import re

from rich import print as pp

import os

from dotenv import load_dotenv

from typing import List, Dict

from datetime import datetime


load_dotenv()

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


def make_github_api_request(api_url:str , headers: dict) -> dict:
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


# def preprocessing_code_pr(code: list) -> list:
#     """
#     Processes a list of dictionaries representing files and their content in a pull request diff format.
#     It removes specific diff markers, assigns line numbers to each line, and excludes lines starting with '-'.
#
#     Args:
#         code (List[Dict[str, str]]): A list of dictionaries where each dictionary represents a file with its content.
#
#     Returns:
#         List[Dict[str, List[Dict[str, str]]]]: A list of dictionaries where each dictionary contains the file name
#         and the list of its lines, each with a line number and content.
#     """
#     pattern_diff = re.compile(r"^(@@).*(@@)\n")
#     pattern_minus = re.compile(r"^-")  # Matches lines starting with '-'
#
#     # Iterate through each file in the code dictionary
#     for file in code:
#         # Remove diff markers (lines starting with '@@' and ending with '@@')
#         file_content = pattern_diff.sub("", file["content"])
#         lines = file_content.split("\n")
#
#         # Prepare to hold the new content with line numbers
#         new_content = []
#         count = 1
#
#         for line in lines:
#             line_numb = {
#                 "line_number": count,
#                 "content": line
#             }
#             if not pattern_minus.match(line):
#                 count += 1
#             new_content.append(line_numb)  #
#
#         file["content"] = new_content
#
#     return code

def preprocessing_code_pr_new(code: list) -> list:
    """
    Processes a list of dictionaries representing files and their content in a pull request diff format.
    It removes specific diff markers, assigns line numbers to each line, and excludes lines starting with '-'.

    Args:
        code (List[Dict[str, str]]): A list of dictionaries where each dictionary represents a file with its content.

    Returns:
        List[Dict[str, List[Dict[str, str]]]]: A list of dictionaries where each dictionary contains the file name
        and the list of its lines, each with a line number and content.
    """
    pattern_diff = re.compile(r"@@ -(\d+,?\d*) \+(\d+,?\d*) @@")
    pattern_minus = re.compile(r"^-")  # Matches lines starting with '-'
    pattern_plus = re.compile(r"^\+")  # Matches lines starting with '-'
    pattern_number = re.compile(r"(\d+),?(\d*)")  #Matches numbers

    # Iterate through each file in the code dictionary
    for file in code:
        # Remove diff markers (lines starting with '@@' and ending with '@@')
        lines = file["content"].split("\n")

        # Prepare to hold the new content with line numbers
        new_content = []
        count = 1

        for line in lines:
            if pattern_diff.match(line):
                diff_lines = pattern_diff.match(line)
                file_start_new_version = int(pattern_number.match(diff_lines.group(2)).group(1))
                count = file_start_new_version
                continue
            line_numb = {
                "line_number": count,
                "content": line
            }
            if not pattern_minus.match(line):
                count += 1
            new_content.append(line_numb)  #

        file["content"] = new_content

    return code


def get_first_comment_date(comments: List[Dict]) -> datetime:
    """
        Returns the earliest comment date from the list of comments.

        Args:
            comments (List[Dict]): A list of comments with date information.

        Returns:
            datetime: The earliest comment date.
        """
    comments_dates = [datetime.strptime(comment["date"], '%Y-%m-%dT%H:%M:%SZ') for comment in comments]
    return min(comments_dates)


# pp(make_github_api_request('https://api.github.com/repos/kuchikihater/gruppirovka/pulls/6', headers = {
#         "Accept": "application/vnd.github+json",
#         'Authorization': f'Bearer {os.getenv("GITHUB_API_KEY")}'
#     }))
