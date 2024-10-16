import os
from typing import List, Dict, Optional
from urllib.parse import urlparse

import requests
from langchain_community.document_loaders import NotionDBLoader
from langchain_core.documents import Document

from logger_setup import *
from rich import print as pp
from dotenv import load_dotenv

load_dotenv()


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
    try:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')

        owner = path_parts[0]
        repo = path_parts[1]
        if path_parts[2] != 'pull':
            logger.error('Invalid GitHub pull request URL format.')
            raise ValueError('Invalid GitHub pull request URL format.')

        pull_number = path_parts[3]
    except (IndexError, ValueError) as e:
        logger.error(f'Error parsing URL: {e}')
        raise ValueError('Invalid GitHub pull request URL.') from e

    logger.info(f"Owner: {owner}, Repo: {repo}, Pull Number: {pull_number}")

    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files"

    # Make the API request to GitHub
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
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

    # Process the response data
    files_data = response.json()
    code = []
    for file in files_data:
        filename = file.get('filename')
        patch = file.get('patch', 'No changes (binary file or new file)')
        code.append({'filename': filename, 'content': patch})

    return code


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


# pp(get_pull_request_content('https://github.com/PJATK-ASI-2024/LAB-2_s22179/pull/1/files'))

pp(get_notion_docs())
