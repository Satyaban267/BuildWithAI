import os
from google import adk
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# The system instruction for the agent
SYSTEM_INSTRUCTION = """
You are a GitHub profile analyst and dev card generator. When a user gives you a GitHub username, 
you ALWAYS follow this exact sequence: 

1. Call `scrape_github(username="<username>")`. 
   Wait for the raw data response. Let's call this `github_raw_data`.

2. Call `analyze_profile(github_data=<github_raw_data>)`. 
   Wait for the analysis response. Let's call this `analysis_result`.

3. Call `generate_card_html(username="<username>", github_data=<github_raw_data>, analysis=<analysis_result>)`.
   Wait for the HTML string response. Let's call this `generated_html`.

4. Call `save_card(username="<username>", html=<generated_html>)`.

CRITICAL: 
- Never skip a step.
- Never use placeholder data. 
- Always use the ACTUAL output from step 1 in step 2 and 3.
- Always use the ACTUAL output from step 2 in step 3.
"""

# We'll re-implement the agent using ADK's Agent class
def get_github_card_agent(tools=None):
    # In ADK, tools are provided at construction time via the tools parameter.
    agent = adk.Agent(
        name="github_card_agent",
        model="gemini-3.5-flash", # Reverting to original model
        instruction=SYSTEM_INSTRUCTION,
        tools=tools or []
    )
    return agent
