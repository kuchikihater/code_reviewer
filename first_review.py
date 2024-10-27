from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from rich import print as pp
from tools import *
from prompts import *
from logger_setup import *
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
import os
import time

# Load environment variables
load_dotenv()

class State(TypedDict):
    message: list

class Answered(BaseModel):
    """
    Model representing a suggestion with line information and file name.
    """
    title: str = Field(description="Title of comment")
    suggestion: str = Field(description="Proposed correction or improvement")
    lines: list[int] = Field(description="Only start line and end line")
    file: str = Field(description="File name")


class ListSuggestion(BaseModel):
    """Model representing a list of suggestions."""
    suggestions: list[Answered] = Field(description="List of suggestions")


def get_pr(state: State):
    """
    Fetches the pull request content.
    """
    start = time.time()
    code = get_pull_request_content(state["message"][0])
    print(f"Pull Request{time.time() - start}")
    return {"message": [code]}


def preprocessing_code(state: State):
    """
    Preprocesses the pull request content to assign lines.
    """
    start = time.time()
    new_code = preprocessing_code_pr(state["message"][0])
    print(f"Assign Lines{time.time() - start}")
    return {"message": [new_code]}


def first_review_invoke(state: State):
    """
    Invoke the LLM with the content of the pull request and additional context from Notion docs.
    """
    logger.info("first_review_invoke() called")

    # Check if the OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        raise ValueError("OPENAI_API_KEY is missing in the environment variables.")

    # Initialize LLM and parser
    try:
        llm = ChatOpenAI(
            api_key=api_key,
            model="gpt-4o"
        )
    except Exception as e:
        logger.error(f"Error while initiating model: {e}")
        raise

    try:
        parser = JsonOutputParser(pydantic_object=ListSuggestion)
    except Exception as e:
        logger.error(f"Error while initiating parser: {e}")
        raise

    # Fetch required content with error handling
    code = state["message"]
    if not code:
        raise ValueError("No content found for the pull request at URL.")

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
        logger.error(f"Error while invoking LLM: {e}")
        response = None

    # Parse the response
    if response:
        return {"message": [response]}
    else:
        logger.error("Empty response from the LLM.")
        return {"message": []}


"""Sets up the StateGraph for processing."""
builder = StateGraph(State)
builder.add_node("GitHub PR", get_pr)
builder.add_node("Assign Lines", preprocessing_code)
builder.add_node("Generate Comments", first_review_invoke)
builder.add_edge(START, "GitHub PR")
builder.add_edge("GitHub PR", "Assign Lines")
builder.add_edge("Assign Lines", "Generate Comments")
builder.add_edge("Generate Comments", END)

graph = builder.compile()

print(graph.invoke({"message": ["https://github.com/kuchikihater/gruppirovka/pull/6"]}))