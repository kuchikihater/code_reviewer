import requests
import prompts
import json
from langchain_community.document_loaders import NotionDBLoader
from langchain_core.prompts import HumanMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
import patchy
from pydantic import BaseModel, Field, validator
import os
from dotenv import load_dotenv
from unidiff import PatchSet
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


def preprocess_code(content):
    lines = content.split('\n')

    start_index = next((i for i, line in enumerate(lines) if line.startswith('+package')), None)

    if start_index is not None:
        processed_code = '\n'.join([line[1:] if line.startswith('+') else line for line in lines[start_index:]])
        return processed_code
    else:
        return "No code found in the content."


class Answered(BaseModel):
    suggestion: str = Field(description="Proposed correction or improvement")
    lines: list[int] = Field(description="Only start line and end line")
    file: str = Field("File name")


class List_Suggestion(BaseModel):
    suggestions: list[Answered] = Field(description="List of suggestions")


def get_full_code(data):
    pull_req = data["pull_request"]
    if not pull_req:
        print("No pull request data found.")
        return
    code = []
    headers = {
        "Accept": "application/vnd.github+json",
        'Authorization': f'Bearer {os.getenv("GITHUB_API_KEY")}'
    }

    url = data["pull_request"]["url"] + "/files"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        files_data = response.json()
        for file in files_data:
            file_dict = {}
            file_dict["filename"] = file['filename']
            file_dict["content"] = file.get('patch', 'No changes (binary file or new file)')
            code.append(file_dict)
        return code
    else:
        print(f'Error: {response.status_code}, {response.json()}')
        return None


def get_commits_from_pr(data):
    pull_req = data.get("pull_request")
    if not pull_req:
        print("No pull request data found.")
        return None

    headers = {
        "Accept": "application/vnd.github+json",
        'Authorization': f'Bearer {os.getenv("GITHUB_API_KEY")}'
    }

    commits_url = pull_req["commits_url"]

    commits_response = requests.get(commits_url, headers=headers)

    if commits_response.status_code == 200:
        commits_data = commits_response.json()
        print(commits_data)
        commits_info = {}

        for commit in commits_data:
            sha = commit["sha"]
            commit_url = f'https://api.github.com/repos/{pull_req["head"]["user"]["login"]}/{pull_req["head"]["repo"]["name"]}/commits/{sha}'
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

                commits_info[sha] = commit_info
            else:
                print(
                    f"Ошибка при получении данных о коммите {sha}: {commit_response.status_code}, {commit_response.text}")
        return commits_info
    else:
        print(f"Ошибка при получении списка коммитов: {commits_response.status_code}")
        return None


def llm_code(data: list):
    loader = NotionDBLoader(
        integration_token=os.getenv("NOTION_API_KEY"),
        database_id="120ffd2db62a800b843bd72e82ec59b1",
        request_timeout_sec=30,  # optional, defaults to 10
    )
    parser = JsonOutputParser(pydantic_object=List_Suggestion)
    print(parser.get_format_instructions())
    docs = loader.load()
    print(docs[0].page_content)
    human_prompt = HumanMessagePromptTemplate.from_template(
        prompts.prompt_template,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            prompts.system_message,
            human_prompt,
        ]
    )
    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0,
        model="gpt-4"
    )
    chain = prompt | llm | parser
    for i in range(len(data)):
        data[i]["content"] = prompts.preprocess_code(data[i].get('content'))
    response = chain.invoke(
        {
            "context": str(docs[0].page_content),
            "code": str(data),
            "format_instructions": parser.get_format_instructions(),
        }
    )
    print(response)
