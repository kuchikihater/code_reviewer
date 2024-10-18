import os
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse

import requests
from langchain_community.document_loaders import NotionDBLoader
from langchain_core.documents import Document

from logger_setup import *
from rich import print as pp
from dotenv import load_dotenv

load_dotenv()


def parse_github_pull_request_url(url):
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


def get_commit_details(owner: str, repo: str, sha: str, headers: Dict[str, str]) -> Dict[str, str]:
    """
    Retrieves detailed information about a specific commit in a GitHub repository.

    Args:
        owner (str): The repository owner.
        repo (str): The repository name.
        sha (str): The commit SHA identifier.
        headers (Dict[str, str]): Headers for the GitHub API request.

    Returns:
        Dict[str, str]: A dictionary with commit details including the commit date and modified files.
    """
    commit_url = f'https://api.github.com/repos/{owner}/{repo}/commits/{sha}'
    commit_response = requests.get(commit_url, headers=headers)

    if commit_response.status_code == 200:
        commit_details = commit_response.json()

        commit_info = {
            "commit_sha": sha,
            "commit_date": commit_details['commit']['author']['date'],
            "files": []
        }

        for file in commit_details.get('files', []):
            file_info = {
                "filename": file['filename'],
                "changes": file.get('patch', 'No changes (binary file or new file)')
            }
            commit_info["files"].append(file_info)

        return commit_info
    else:
        logger.error(f"Error fetching commit details for {sha}: {commit_response.status_code}, {commit_response.text}")
        return {}


# Needs to be changed to webhook in the future
def get_pull_request_content(url: str) -> List[Dict[str, str]]:
    """
    Fetch the content of files changed in a GitHub pull request.

    Args:
        url (str): The URL of the GitHub pull request.

    Returns:
        List[Dict[str, str]]: A list of dictionaries containing filenames and their content changes.

    Raises:
        ValueError: If the URL cannot be parsed or required data is missing.
        requests.exceptions.RequestException: If an error occurs while making the HTTP request.
        EnvironmentError: If the GitHub API key is not found in environment variables.
    """
    logger.info('get_pull_request_content() called')

    # Retrieve the GitHub API key from environment variables
    api_key = os.getenv("GITHUB_API_KEY")
    if not api_key:
        logger.error('GitHub API key not found in environment variables.')
        raise EnvironmentError('GitHub API key not found in environment variables.')

    headers = {
        "Accept": "application/vnd.github+json",
        'Authorization': f'Bearer {api_key}'
    }

    # Parse the GitHub pull request URL to extract owner, repo, and pull number
    owner, repo, pull_number = parse_github_pull_request_url(url)

    logger.info(f"Owner: {owner}, Repo: {repo}, Pull Number: {pull_number}")

    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files"

    # Make the API request to GitHub Process the response data
    files_data = make_github_api_request(api_url, headers)
    code = []
    for file in files_data:
        filename = file.get('filename')
        patch = file.get('patch', 'No changes (binary file or new file)')
        code.append({'filename': filename, 'content': patch})

    return code


def get_pull_request_commits_content(url: str) -> Dict[str, Dict[str, str]]:
    """
    Fetches commit details for a given pull request from a GitHub repository.

    Args:
        url (str): The URL of the GitHub pull request.

    Returns:
        Dict[str, Dict[str, str]]: A dictionary where each key is a commit SHA,
        and each value is another dictionary containing details of that commit.
    """
    logger.info('get_pull_request_commits_content() called')

    # Retrieve the GitHub API key from environment variables
    api_key = os.getenv("GITHUB_API_KEY")
    if not api_key:
        logger.error('GitHub API key not found in environment variables.')
        raise EnvironmentError('GitHub API key not found in environment variables.')

    headers = {
        "Accept": "application/vnd.github+json",
        'Authorization': f'Bearer {api_key}'
    }

    # Parse the GitHub pull request URL to extract owner, repo, and pull number

    owner, repo, pull_number = parse_github_pull_request_url(url)

    logger.info(f"Owner: {owner}, Repo: {repo}, Pull Number: {pull_number}")

    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/commits"

    # Make the API request to GitHub
    commits = make_github_api_request(api_url, headers)
    if not commits:
        logger.error(f'No commits were found at {api_url}')
        return {}

    commits_info = {}

    for commit in commits:
        sha = commit.get("sha")
        if not sha:
            logger.warning("No SHA found for commit, skipping.")
            continue

        commit_info = get_commit_details(owner, repo, sha, headers)
        if commit_info:
            commits_info[sha] = commit_info
        else:
            logger.error(f"Failed to retrieve details for commit {sha}")
            raise

    return commits_info

def get_pull_request_comments(url: str) -> List[Dict[str, str]]:
    """
    Retrieves comments from a pull request along with the code they are related to and the comment's date.

    Args:
        url (str): The URL of the GitHub pull request.

    Returns:
        List[Dict[str, str]]: A list of dictionaries containing the comment text, code snippet, and the date.
    """
    logger.info('get_pull_request_comments() called')

    # Retrieve the GitHub API key from environment variables
    api_key = os.getenv("GITHUB_API_KEY")
    if not api_key:
        logger.error('GitHub API key not found in environment variables.')
        raise EnvironmentError('GitHub API key not found in environment variables.')

    headers = {
        "Accept": "application/vnd.github+json",
        'Authorization': f'Bearer {api_key}'
    }

    # Parse the URL to extract the owner, repository name, and pull request number
    owner, repo, pull_number = parse_github_pull_request_url(url)

    logger.info(f"Owner: {owner}, Repo: {repo}, Pull Number: {pull_number}")

    # URL to get comments from the pull request
    comments_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/comments"

    # Make a request to GitHub API to get the comments
    try:
        response = requests.get(comments_url, headers=headers)
        response.raise_for_status()  # Raise exception for unsuccessful requests
        comments_data = response.json()  # Parse response as JSON
    except requests.RequestException as e:
        logger.error(f"Error fetching comments: {e}")
        return []

    # Process comments and collect the needed information
    comments_info = []
    for comment in comments_data:
        comment_info = {
            "filename": comment["path"],  # File related to the comment
            "code": comment.get("diff_hunk", ""),  # Code related to the comment (diff hunk)
            "comment": comment["body"],  # Text of the comment
            "date": comment["updated_at"]  # Date when the comment was updated
        }
        comments_info.append(comment_info)

    return comments_info

def get_notion_docs(
        database_id: str = '120ffd2db62a800b843bd72e82ec59b1',
        page_id: Optional[str] = None
) -> List[Document]:
    """
    Fetch documents from a Notion database, optionally filtering by a specific page ID.

    Args:
        database_id (str): The ID of the Notion database to query.
        page_id (Optional[str]): The ID of the specific page to retrieve.

    Returns:
        List[Document]: A list of Document objects retrieved from the Notion database.

    Raises:
        EnvironmentError: If the NOTION_API_KEY environment variable is not set.
        ValueError: If no documents are found with the specified page_id.
        Exception: If an error occurs during the loading of documents.
    """
    logger.info("get_notion_docs() called")

    # Retrieve the Notion API key from environment variables
    notion_api_key = os.getenv("NOTION_API_KEY")
    if not notion_api_key:
        logger.error("NOTION_API_KEY not found in environment variables.")
        raise EnvironmentError("NOTION_API_KEY not found in environment variables.")

    # Initialize the NotionDBLoader
    try:
        loader = NotionDBLoader(
            integration_token=notion_api_key,
            database_id=database_id,
            request_timeout_sec=30  # Optional, defaults to 10
        )
        docs = loader.load()
    except Exception as e:
        logger.error("Error while initiating NotionDBLoader: %s", e)
        raise

    # Filter documents by page_id if provided
    if page_id is not None:
        docs = [doc for doc in docs if doc.metadata.get('id') == page_id]
        if docs:
            logger.info("Document with page_id %s found.", page_id)
        else:
            logger.error("No documents found with page_id: %s", page_id)
            raise ValueError(f"No documents found with page_id: {page_id}")

    # Check if any documents were loaded
    if not docs:
        logger.error("No documents found in the database.")
        raise ValueError("No documents found in the database.")

    logger.info("Loaded %d document(s).", len(docs))
    return docs


pp(get_pull_request_content('https://github.com/kuchikihater/gruppirovka/pull/6'))
