from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from prompts import *
from tools import *
from dotenv import load_dotenv
from os import getenv

from rich import print as pp

load_dotenv()


class Answered(BaseModel):
    """Model representing a suggestion with line information and file name."""
    title: str = Field(description="Title of comment")
    suggestion: str = Field(description="Proposed correction or improvement")
    lines: list[int] = Field(description="Only start line and end line")
    file: str = Field(description="File name")


class ListSuggestion(BaseModel):
    """Model representing a list of suggestions."""
    suggestions: list[Answered] = Field(description="List of suggestions")


api_key = getenv("OPENAI_API_KEY")

llm = ChatOpenAI(
    api_key=api_key,
    model="gpt-4o-mini"
)

parser = JsonOutputParser(pydantic_object=ListSuggestion)

create_initial_comments_prompt = PromptTemplate.from_template(prompt_full_code_template)
filter_comments_prompt = PromptTemplate.from_template(prompt_filter_comments)

filter_comments_chain = filter_comments_prompt | llm | parser
create_initial_comments_chain = create_initial_comments_prompt | llm | parser


class InputState(TypedDict):
    # Those 2 must be provided by user when we invoke graph
    pull_request_link: str  # link to pull request
    notion_doc_id: str  # page_id for notion doc
    notion_db_id: str  # db_id for notion doc


class OutputState(TypedDict):
    initial_comments: list  # comments from the first try
    dropped_comments: list  # deleted engineering or non informative comments
    filtered_comments: list  # final set of comments that model generated


class OverallState(TypedDict):
    # Those 2 must be provided by user when we invoke graph
    pull_request_link: str  # link to pull request
    notion_doc_id: str  # page_id for notion doc
    notion_db_id: str  # db_id for notion doc

    raw_code: list  # raw code from pull request
    preprocessed_code: list  # line assigned code
    initial_comments: list  # comments from the first try
    dropped_comments: list  # deleted engineering or non informative comments
    filtered_comments: list  # final set of comments that model generated
    tech_task_description: List[Document]  # technical task information


def get_tech_task_description(state: OverallState) -> OverallState:
    state['tech_task_description'] = get_notion_docs(database_id=state["notion_db_id"],page_id=state['notion_doc_id'])
    return state


def get_raw_code(state: InputState) -> OverallState:
    state['raw_code'] = get_pull_request_content(state["pull_request_link"])
    return state


def preprocessing_code(state: OverallState):
    state['preprocessed_code'] = preprocessing_code_pr(state["raw_code"])
    return state


def generate_comment_invoke(state: OverallState):
    # Create Comments for PR
    first_round_comments_generated = create_initial_comments_chain.invoke({
        "code": state["preprocessed_code"],
        "context": state['tech_task_description'],
        "format_instructions": parser.get_format_instructions()
    })

    state['initial_comments'] = first_round_comments_generated

    return state


def filter_comment_invoke(state: OverallState) -> OutputState:
    # Filter Comments
    filtered_comments_response = filter_comments_chain.invoke({
        "comments": state["initial_comments"],
        "format_instructions": parser.get_format_instructions()
    })

    state['filtered_comments'] = filtered_comments_response

    state['dropped_comments'] = [comment for comment in state['initial_comments'] if
                                 comment not in state['filtered_comments']]

    return state


builder = StateGraph(OverallState, input=InputState, output=OutputState)
builder.add_node("GitHub PR", get_raw_code)
builder.add_node("Get Tech Task Description", get_tech_task_description)
builder.add_node("Assign Lines", preprocessing_code)
builder.add_node("Generate Comments", generate_comment_invoke)
builder.add_node("Filter Comments", filter_comment_invoke)

builder.add_edge(START, "GitHub PR")
builder.add_edge("GitHub PR", "Get Tech Task Description")
builder.add_edge("Get Tech Task Description", "Assign Lines")
builder.add_edge("Assign Lines", "Generate Comments")
builder.add_edge("Generate Comments", "Filter Comments")
builder.add_edge("Filter Comments", END)

graph = builder.compile()

pp(graph.invoke({"pull_request_link": "https://github.com/CorporationX/god_bless/pull/14060",
                 "notion_doc_id": "120ffd2d-b62a-8058-93e2-e14363c7b31e", "notion_db_id": "120ffd2db62a800b843bd72e82ec59b1"}))
