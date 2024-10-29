import os
from typing import List, Dict, Optional

import requests
from langchain_community.document_loaders import NotionDBLoader
from langchain_core.documents import Document

from logger_setup import *
from rich import print as pp
from dotenv import load_dotenv

from utils import parse_github_pull_request_url, make_github_api_request, apply_diff

from datetime import datetime

import json
import re

load_dotenv()


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
        # Filter out deleted files
        filtered_files = [
            file for file in commit_details.get("files", [])
            if file.get("status") != "removed"
        ]

        # Update the commit info with filtered files
        commit_details["files"] = filtered_files

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

    commits_info = []

    for commit in commits:
        sha = commit.get("sha")
        if not sha:
            logger.warning("No SHA found for commit, skipping.")
            continue

        commit_info = get_commit_details(owner, repo, sha, headers)
        if commit_info:
            # Filter out deleted files
            filtered_files = [
                file for file in commit_info.get("files", [])
                if file.get("status") != "removed"
            ]
            commits_info.append(commit_info)
        else:
            logger.error(f"Failed to retrieve details for commit {sha}")
            raise

    return commits_info


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
        'Authorization': f'Bearer {api_key}',
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # Parse the URL to extract the owner, repository name, and pull request number
    owner, repo, pull_number = parse_github_pull_request_url(url)

    logger.info(f"Owner: {owner}, Repo: {repo}, Pull Number: {pull_number}")

    # Fetch pull request details to get the creator's username
    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
    pull_request_data = make_github_api_request(pr_url, headers)
    pr_creator = pull_request_data["user"]["login"]

    # URL to get code comments from the pull request
    code_comments_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/comments"

    # URL to get general comments from the pull request (via issue comments API)
    issue_comments_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pull_number}/comments"

    # Make a request to GitHub API to get both code and general comments
    code_comments_data = make_github_api_request(code_comments_url, headers)
    issue_comments_data = make_github_api_request(issue_comments_url, headers)

    comments_info = []

    # Process code comments and collect the needed information
    for comment in code_comments_data:
        if comment["user"]["login"] != pr_creator:
            comment_info = {
                "filename": comment["path"],  # File related to the comment
                "code": comment.get("diff_hunk", ""),  # Code related to the comment (diff hunk)
                "comment": comment["body"],  # Text of the comment
                "date": comment["updated_at"]  # Date when the comment was updated
            }
            comments_info.append(comment_info)

    # Process general comments and collect the needed information
    pp(issue_comments_data)
    for comment in issue_comments_data:
        if comment["user"]["login"] != pr_creator:
            comment_info = {
                "filename": None,  # No file is associated with a general comment
                "code": None,  # No code is associated with a general comment
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


def preprocessing_code_pr(code: list) -> list:
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
    pattern_number = re.compile(r"(\d+),?(\d*)")  # Matches numbers

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


def get_commits_before_date_comment(commits: List[Dict], date: datetime) -> List[Dict]:
    """
        Returns commits that were made before a given firts comment.

        Args:
            commits (List[Dict]): A list of commits with their metadata (e.g., commit date).
            date (datetime): The date of the comment (in ISO format) to filter commits.

        Returns:
            List[Dict]: A list of commits made before the comment date.
    """
    filtered_commits = [commit for commit in commits if
                        datetime.strptime(commit["commit_date"], '%Y-%m-%dT%H:%M:%SZ') < date]
    return filtered_commits


def process_pull_request_diffs(index: int, filepath: str) -> List[Dict[str, str]]:
    """
    Process the diffs from the pull request and reconstruct the file content.

    Args:
        index (int): Index of the pull request to process.
        filepath (str): Path to the JSON file containing pull request data.

    Returns:
        List[Dict[str, str]]: A list of dictionaries with filename and content.
    """

    # Load the JSON file
    with open(filepath, "r") as f:
        result = json.load(f)

    # Extract the specific pull request by index
    pull_request = result[index]

    files_content = {}

    # Apply diffs to the corresponding files
    for timestamp, contents in pull_request["content"].items():
        for content in contents:
            filename = content["filename"]
            diff = content["changes"]
            # Use setdefault to initialize the file content if not present
            files_content.setdefault(filename, "")
            # Apply the diff to the file content
            files_content[filename] = apply_diff(files_content[filename], diff)

    # Construct the list of files with their contents using list comprehension
    return [{"filename": filename, "content": content} for filename, content in files_content.items()]

# pp(get_pull_request_comments("https://github.com/CorporationX/god_bless/pull/11585"))
