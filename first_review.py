from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from rich import print as pp
from tools import *
from prompts import *
from logger_setup import *
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
import os
import sys

# Load environment variables
load_dotenv()


class Answered(BaseModel):
    """Model representing a suggestion with line information and file name."""
    suggestion: str = Field(description="Proposed correction or improvement")
    lines: list[int] = Field(description="Only start line and end line")
    file: str = Field(description="File name")


class ListSuggestion(BaseModel):
    """Model representing a list of suggestions."""
    suggestions: list[Answered] = Field(description="List of suggestions")


def llm_invoke(url: str):
    """
    Invoke the LLM with the content of the pull request and additional context from Notion docs.

    Args:
        url (str): URL of the pull request to fetch content.

    Returns:
        Response from the LLM after processing the input, or None in case of an error.
    """
    logger.info("llm_invoke() called")


    # Check if the OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        raise ("OPENAI_API_KEY is missing in the environment variables.")

    # Initialize LLM and parser
    try:
        llm = ChatOpenAI(
            api_key=api_key,
            model="gpt-4o"
        )
    except Exception as e:
        logger.error(f"Error while initiating model:{e}")
        raise

    try:
        parser = JsonOutputParser(pydantic_object=ListSuggestion)
    except Exception as e:
        logger.error(f"Error while initiating parser:{e}")
        raise

    # Fetch required content with error handling
    pr_content = get_pull_request_content(url)
    if not pr_content:
        raise ValueError(f"No content found for the pull request at URL: {url}")

    nb_content = get_notion_docs(page_id="120ffd2d-b62a-8058-93e2-e14363c7b31e")
    if not nb_content:
        raise ValueError("No content found from Notion documents.")

    # Prepare the prompt
    prompt = PromptTemplate.from_template(prompt_full_code_template)

    # Chain the components and invoke LLM
    chain = prompt | llm | parser
    try:
        response = chain.invoke({
            "code": pr_content,
            "context": nb_content,
            "format_instructions": parser.get_format_instructions()
        })
    except Exception as e:
        logger.error(f"Error while invoking LLM:{e}")
    # Parse the response
    if response:
        return response
    else:
        logger.error("Empty response from the LLM.")
        return None


# Test the function
# pp(llm_invoke("https://github.com/kuchikihater/gruppirovka/pull/6/files#diff-fe417ff2fff8aa4043957482e5fa1f9d80971a52bf7f6f8389b9d67845055c47R4"))
