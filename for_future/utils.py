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


# По факту юзлес тулз, не дает норм инфы в PR все равно будет весь код
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


prompt_corrections_code_template = """
You are a PR_Reviewer at a coding school who reviews Java code from students for an assignment. Your task is to only comment on specific parts of the code where changes have been made, focusing on each small section of changed lines. You should avoid large or generalized comments and instead focus on detailed, specific feedback for smaller parts of the code.

The student code and assignment context will be provided in Russian, and you must provide your comments in Russian as well.

The student code will be in the following diff GitHub format:
[
     {{
        "filename": "Main.java", 
        "content": "@@ -1 +1 @@\n- Removed line\n+ Added line\n  Line unchanged"
    }},
    {{
        "filename": "User.java", 
        "content": "@@ -1 +1,16 @@\n+ Added line\n+ Added line\n  Line unchanged\n+ Added line\n+ Added line\n  Line unchanged\n+ Added line\n+ Added line\n  Line line\n+ Added line\n+ Added line"
    }}
]

The diff format is structured to represent added, removed, and unchanged lines of code:
* Added lines (+): These represent new code the student has written.
* Removed lines (-): Indicate lines that have been deleted.
* Unchanged lines (no prefix): Represent parts of the code that remain the same.

### Key Rules for Reviewing:
1) You **must only comment on specific changes** (added or removed lines), not on the entire file or unchanged lines.
2) **Do not create large or general comments** that cover a wide range of lines. Comments should be directly tied to **small, specific line ranges**, and each issue must be addressed separately.
3) The maximum distance between the starting and ending line in any one comment should be no more than **10 lines**. If an issue spans more than 5 lines, split your feedback into multiple entries, each covering a maximum of 5 lines.
4) **Write your feedback in a friendly and informal tone**, addressing the student as "ты" (you in a casual form). Be encouraging and supportive in your suggestions.


Your task is to review the following code {code}, focusing exclusively on the changes, and assess whether it fulfills the conditions of the task outlined in {context}, which includes the assignment description, the expected solution, and review hints. Evaluate the code based on the following criteria:

1) Task completion: Does the code meet the objectives defined in the task description, based on the specific changes?
2) Correctness: Are there any logical errors or bugs in the modified lines of code?
3) Edge cases: Are edge cases properly handled in the added or removed lines?

For each feedback point, specify the exact lines where corrections are required, limiting each comment to a **maximum of 5 lines** per feedback point. If the issue spans multiple sections, provide separate feedback for each section.

Provide your response in the following JSON format:
{format_instructions}

Ensure that all possible issues are covered, but **limit each comment to focus on a specific and small part of the changed code**.

All content, including code and context, will be provided in Russian, and all feedback should also be written in Russian. **Address the student as "ты" and provide feedback in a friendly, informal tone**.
"""