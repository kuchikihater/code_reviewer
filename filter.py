from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field, ValidationError
from prompts import *
from tools import *
from dotenv import load_dotenv
from os import getenv
import time
import json
from rich import print as pp


load_dotenv()


class State(TypedDict):
    message: list


class Answered(BaseModel):
    """Model representing a suggestion with line information and file name."""
    title: str = Field(description="Title of comment")
    suggestion: str = Field(description="Proposed correction or improvement")
    lines: list[int] = Field(description="Only start line and end line")
    file: str = Field(description="File name")


class ListSuggestion(BaseModel):
    """Model representing a list of suggestions."""
    suggestions: list[Answered] = Field(description="List of suggestions")


def get_pr(state: State):
    start = time.time()
    code = get_pull_request_content(state["message"][0])
    print(f"Pull Request{time.time() - start}")
    return {"message": [code]}


def get_code_for_testing(state: dict):
    # Load the JSON data from file
    with open("studio/data.json", "r") as f:
        result = json.load(f)

    # Extract the pull request by matching the URL from the state
    pull_request = next((pr for pr in result if pr["url"] == state["message"][0]), None)

    if pull_request:
        # Find the index of the pull request
        index = result.index(pull_request)
        # Process the pull request diffs and get the code
        code = process_pull_request_diffs(index, "studio/data.json")
        return {"message": [code]}
    else:
        logger.error("Pull Request not found in dataset.")
        raise ValueError("Pull Request not found in dataset.")


def preprocessing_code(state: State):
    start = time.time()
    new_code = preprocessing_code_pr(state["message"][0])
    print(f"Assign Lines{time.time() - start}")
    return {"message": [new_code]}


def model_invoke(state: State):
    start = time.time()
    # Check if the OpenAI API key is available
    api_key = getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        raise "OPENAI_API_KEY is missing in the environment variables."

    # Initialize LLM and parser
    try:
        llm = ChatOpenAI(
            api_key=api_key,
            model="gpt-4o-mini"
        )
    except Exception as e:
        logger.error(f"Error while initiating model:{e}")
        raise

    try:
        parser = JsonOutputParser(pydantic_object=ListSuggestion)
    except Exception as e:
        logger.error(f"Error while initiating parser:{e}")
        raise

    # PR Code
    code = state["message"][0]
    if not code:
        raise ValueError(f"No content found for the pull request at URL:")

    # Get Notion File
    nb_content = get_notion_docs(page_id="120ffd2d-b62a-8058-93e2-e14363c7b31e")
    if not nb_content:
        raise ValueError("No content found from Notion documents.")

    # Prepare the prompt
    prompt = PromptTemplate.from_template(prompt_full_code_template)

    # Chain the components and invoke LLM
    chain = prompt | llm | parser
    try:
        response = chain.invoke({
            "code": code,
            "context": nb_content,
            "format_instructions": parser.get_format_instructions()
        })
    except Exception as e:
        logger.error(f"Error while invoking LLM:{e}")
    print(f"Generate Comments{time.time() - start}")
    # Parse the response
    if response:
        return {"message": [response]}
    else:
        logger.error("Empty response from the LLM.")
        return {"message": []}


# Здесь продолжить
def filter_comments(state: State):
    start = time.time()
    # Check if the OpenAI API key is available
    api_key = getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        raise "OPENAI_API_KEY is missing in the environment variables."

    # Initialize LLM and parser
    try:
        llm = ChatOpenAI(
            api_key=api_key,
            model="gpt-4o-mini"
        )
    except Exception as e:
        logger.error(f"Error while initiating model:{e}")
        raise

    try:
        parser = JsonOutputParser(pydantic_object=ListSuggestion)
    except Exception as e:
        logger.error(f"Error while initiating parser:{e}")
        raise

    code = state["message"][0]
    if not code:
        raise ValueError(f"No content found for the pull request at URL:")

    # Prepare the prompt
    prompt = PromptTemplate.from_template(prompt_filter_comments)

    # Chain the components and invoke LLM
    chain = prompt | llm | parser
    try:
        response = chain.invoke({
            "comments": code,
            "format_instructions": parser.get_format_instructions()
        })
    except Exception as e:
        logger.error(f"Error while invoking LLM:{e}")

    print(f"Filter Comments{time.time() - start}")
    # Parse the response
    if response:
        return {"message": [response]}
    else:
        logger.error("Empty response from the LLM.")
        return {"message": []}


builder = StateGraph(State)
builder.add_node("GitHub PR", get_pr)
builder.add_node("Test Pull Request", get_code_for_testing)
builder.add_node("Assign Lines", preprocessing_code)
builder.add_node("Generate Comments", model_invoke)
builder.add_node("Filter Comments", filter_comments)

builder.add_edge(START, "GitHub PR")

builder.add_edge("GitHub PR", "Test Pull Request")
builder.add_edge("Test Pull Request", "Assign Lines")
builder.add_edge("Assign Lines", "Generate Comments")
builder.add_edge("Generate Comments", "Filter Comments")
builder.add_edge("Filter Comments", END)

graph = builder.compile()


# pp(graph.invoke({"message": ["https://github.com/CorporationX/god_bless/pull/14060"]}))


