from tools import get_commits_before_date_comment, get_pull_request_commits_content, get_pull_request_comments, process_pull_request_diffs
from utils import get_first_comment_date
from rich import print as pp
from datetime import datetime
import json
import time
from tqdm import tqdm
from langsmith import Client
import pandas as pd


gruppirovka_pull_requests = [
    "https://github.com/CorporationX/god_bless/pull/11100",
    "https://github.com/CorporationX/god_bless/pull/11045",
    "https://github.com/CorporationX/god_bless/pull/11009",
    "https://github.com/CorporationX/god_bless/pull/10881",
    "https://github.com/CorporationX/god_bless/pull/8593",
    "https://github.com/CorporationX/god_bless/pull/8491",
    "https://github.com/CorporationX/god_bless/pull/8410",
    "https://github.com/CorporationX/god_bless/pull/7846",
    "https://github.com/CorporationX/god_bless/pull/6192"
]

meta_universe_pull_requests = [
    "https://github.com/CorporationX/god_bless/pull/12393",
    "https://github.com/CorporationX/god_bless/pull/12364",
    "https://github.com/CorporationX/god_bless/pull/12133",
    "https://github.com/CorporationX/god_bless/pull/11887",
    "https://github.com/CorporationX/god_bless/pull/11752",
    "https://github.com/CorporationX/god_bless/pull/11654",
    "https://github.com/CorporationX/god_bless/pull/11585",
    "https://github.com/CorporationX/god_bless/pull/9471"
]

file_path = "data.json"
results = []
#
# for gruppirovka_pull_request in tqdm(gruppirovka_pull_requests, desc="Processing Gruppirovka Pull Requests"):
#     time.sleep(5)
#     # Create a dictionary for the pull request data
#     pull_request = {
#         "task_name": "Группировка пользователей по возрасту",
#         "url": gruppirovka_pull_request
#     }
#
#     # Retrieve commits and comments for the pull request
#     commits = get_pull_request_commits_content(gruppirovka_pull_request)
#     time.sleep(5)
#     comments = get_pull_request_comments(gruppirovka_pull_request)
#
#     # Get the date of the first comment
#     first_comment_date = get_first_comment_date(comments)
#
#     # Filter commits that occurred before the first comment date
#     filtered_commits = get_commits_before_date_comment(commits, first_comment_date)
#
#     # Store the filtered commits in a structured format
#     pull_request["content"] = {str(filtered_commit["commit_date"]): filtered_commit["files"] for filtered_commit in filtered_commits}
#
#     pull_request["comments"] = [comment for comment in comments if 0 <= (datetime.strptime(comment["date"], '%Y-%m-%dT%H:%M:%SZ') - first_comment_date).total_seconds() <= 3600]
#     results.append(pull_request)
#
# for meta_universe_pull_request in tqdm(meta_universe_pull_requests, desc="Processing Meta Universe Pull Requests"):
#     time.sleep(5)
#     # Create a dictionary for the pull request data
#     pull_request = {
#         "task_name": "Meta-вселенная?",
#         "url": meta_universe_pull_request
#     }
#
#     # Retrieve commits and comments for the pull request
#     commits = get_pull_request_commits_content(meta_universe_pull_request)
#     time.sleep(5)
#     comments = get_pull_request_comments(meta_universe_pull_request)
#
#     # Get the date of the first comment
#     first_comment_date = get_first_comment_date(comments)
#
#     # Filter commits that occurred before the first comment date
#     filtered_commits = get_commits_before_date_comment(commits, first_comment_date)
#
#     # Store the filtered commits in a structured format
#     pull_request["content"] = {str(filtered_commit["commit_date"]): filtered_commit["files"] for filtered_commit in filtered_commits}
#
#     pull_request["comments"] = [comment for comment in comments if 0 <= (datetime.strptime(comment["date"], '%Y-%m-%dT%H:%M:%SZ') - first_comment_date).total_seconds() <= 3600]
#     results.append(pull_request)
#
# with open(file_path, "w") as outfile:
#     json.dump(results, outfile, indent=4, ensure_ascii=False)

# with open(file_path, "r") as f:
#     results = json.load(f)
#
#
# for pull_request in tqdm(results, desc = "Processing Pull Requests"):
#     # Find the index of the pull request
#     index = results.index(pull_request)
#     # Process the pull request diffs and get the code
#     results[index]["content"] = process_pull_request_diffs(index, "data.json")
#
# with open(file_path, "w") as f:
#     json.dump(results, f, indent=4, ensure_ascii=False)

#
client = Client()
dataset_name = "FAANG_Academy_Pull_Reqeusts"

dataset = client.create_dataset(dataset_name, description="FAANG_Academy Pull Requests for Test")
