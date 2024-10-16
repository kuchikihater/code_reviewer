from langchain_core.prompts import SystemMessagePromptTemplate

system_message = SystemMessagePromptTemplate.from_template(
    "You are a helpful assistant that reviews code.",
)


prompt_template = """
Please review the following Java code (located between triple commas), which represents the solution to a problem completed by a student. 
The context (located between triple hashes) includes the problem statement, the reference solution, and several hints. 
Look at the student's code, given the context, and find **all the bugs and areas for improvement**.
For each problem, identify the beginning and ending line of the problem in the code.  
Return **only lines and explanations** without reproducing any part of the original code.

Proceed according to the following principles:
1) Look carefully at the context, there you can find a reference solution for what the student's code should look like.
2) Don't point out very common errors.
3) Look very carefully at the hints in the context, they will help you pick up comments.
4) Make sure to point out **no problems** if they are present.
5) Don't number your comments.
6) Only return the start and end line number of the wrong part of the code, e.g. [5,20].
7) Give suggestions in **Russian**

###
Context: This context contains a description of the problem, a reference solution, and helpful hints:
{context}
###

,,,
Student Java code: {code}
,,,

For each problem identified, provide your response in the following format:  
{format_instructions}

Make sure you have identified **all** possible problems for improvement. Each problem should be described separately and include explanations for all relevant lines of code. 
"""
