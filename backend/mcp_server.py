from fastmcp import FastMCP
import httpx
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

from typing import Any

mcp = FastMCP("GitHubDevCardGenerator")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@mcp.tool()
async def scrape_github(username: str) -> dict:
    """Fetch and aggregate GitHub profile and repository data."""
    print(f"DEBUG: Scraping GitHub for {username}")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    async with httpx.AsyncClient() as http_client:
        # Fetch Profile
        user_resp = await http_client.get(f"https://api.github.com/users/{username}", headers=headers)
        user_resp.raise_for_status()
        user_data = user_resp.json()

        # Fetch Repos
        repos_resp = await http_client.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=50", headers=headers)
        repos_resp.raise_for_status()
        repos_data = repos_resp.json()

    # Aggregate Top 6 Repos
    top_repos = sorted(repos_data, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
    formatted_repos = [
        {
            "name": r.get("name", "Unknown"),
            "stars": r.get("stargazers_count", 0),
            "language": r.get("language", "Unknown"),
            "description": r.get("description", "")
        } for r in top_repos
    ]

    # Aggregate Languages
    languages = [r["language"] for r in repos_data if r.get("language")]
    lang_counts = Counter(languages).most_common(5)

    result = {
        "name": user_data.get("name"),
        "bio": user_data.get("bio"),
        "location": user_data.get("location"),
        "avatar_url": user_data.get("avatar_url"),
        "public_repos": user_data.get("public_repos", 0),
        "followers": user_data.get("followers", 0),
        "top_repos": formatted_repos,
        "most_used_languages": [l[0] for l in lang_counts]
    }
    print(f"DEBUG: Scrape result: {list(result.keys())}")
    return result

@mcp.tool()
async def analyze_profile(github_data: dict) -> dict:
    """Use Gemini 3.5 Flash to analyze profile data and determine a developer persona."""
    # Robustness: handle if it's somehow passed as a string despite the dict hint
    if isinstance(github_data, str):
        try:
            github_data = json.loads(github_data)
        except json.JSONDecodeError:
            print(f"DEBUG: Failed to parse github_data string: {github_data[:100]}...")
    
    print(f"DEBUG: Analyzing profile for data with keys: {list(github_data.keys()) if isinstance(github_data, dict) else type(github_data)}")
    prompt = f"""
    Analyze this GitHub data and return a JSON object:
    Data: {json.dumps(github_data) if isinstance(github_data, dict) else str(github_data)}

    JSON structure:
    {{
        "developer_vibe": "1 sentence personality",
        "top_skills": ["list of 3 skills"],
        "fun_fact": "clever inference from repos",
        "card_theme": "one of: 'hacker', 'builder', 'researcher', 'designer', 'open-source-hero'"
    }}
    """
    
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    analysis = json.loads(response.text)
    print(f"DEBUG: AI Analysis output: {analysis}")
    return analysis

@mcp.tool()
async def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """Generate a themed HTML card based on the analysis and data."""
    # Ensure inputs are dicts
    if isinstance(github_data, str):
        try:
            github_data = json.loads(github_data)
        except json.JSONDecodeError:
            pass
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except json.JSONDecodeError:
            pass

    print(f"DEBUG: Generating HTML for {username}")
    print(f"DEBUG: github_data keys: {list(github_data.keys()) if isinstance(github_data, dict) else type(github_data)}")
    print(f"DEBUG: analysis keys: {list(analysis.keys()) if isinstance(analysis, dict) else type(analysis)}")

    theme_colors = {
        "hacker": {"bg": "#0d1117", "text": "#c9d1d9", "accent": "#238636"},
        "builder": {"bg": "#161b22", "text": "#c9d1d9", "accent": "#58a6ff"},
        "researcher": {"bg": "#0d1117", "text": "#c9d1d9", "accent": "#bc8cff"},
        "designer": {"bg": "#161b22", "text": "#c9d1d9", "accent": "#f78166"},
        "open-source-hero": {"bg": "#0d1117", "text": "#c9d1d9", "accent": "#3fb950"}
    }
    
    theme = theme_colors.get(analysis.get("card_theme", "builder"), theme_colors["builder"])
    
    # Defensive access to top_repos
    top_repos = github_data.get("top_repos", []) if isinstance(github_data, dict) else []
    
    repo_list = "".join([
        f"<li><strong>{r.get('name', 'N/A')}</strong> ({r.get('stars', 0)} ⭐) - {r.get('language', 'N/A')}</li>"
        for r in top_repos[:3]
    ])
    
    skills = "".join([f"<span class='badge'>{s}</span>" for s in analysis.get("top_skills", [])])

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; background: transparent; color: {theme['text']}; display: flex; justify-content: center; align-items: center; margin: 0; }}
            .card {{ border: 1px solid #30363d; border-radius: 12px; padding: 24px; width: 350px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); background: {theme['bg']}; }}
            .avatar {{ width: 80px; height: 80px; border-radius: 50%; margin-bottom: 16px; border: 3px solid {theme['accent']}; }}
            h2 {{ margin: 0 0 8px 0; color: {theme['accent']}; }}
            .vibe {{ font-style: italic; margin-bottom: 16px; font-size: 0.9em; color: #8b949e; }}
            .badge {{ background: {theme['accent']}33; color: {theme['accent']}; border: 1px solid {theme['accent']}66; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 4px; }}
            .stats {{ display: flex; justify-content: space-between; margin: 16px 0; font-size: 0.85em; border-top: 1px solid #30363d; padding-top: 12px; }}
            ul {{ list-style: none; padding: 0; font-size: 0.85em; }}
            li {{ margin-bottom: 8px; padding: 8px; background: rgba(255,255,255,0.03); border-radius: 6px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <img src="{github_data.get('avatar_url', '') if isinstance(github_data, dict) else ''}" class="avatar">
            <h2>{github_data.get('name', username) if isinstance(github_data, dict) else username}</h2>
            <p class="vibe">{analysis.get('developer_vibe', 'A passionate developer.')}</p>
            <div class="skills">{skills}</div>
            <div class="stats">
                <span>📦 {github_data.get('public_repos', 0) if isinstance(github_data, dict) else 0} Repos</span>
                <span>👥 {github_data.get('followers', 0) if isinstance(github_data, dict) else 0} Followers</span>
            </div>
            <p><strong>Top Projects:</strong></p>
            <ul>{repo_list}</ul>
            <p style="font-size: 0.7em; margin-top: 16px; opacity: 0.7;">💡 {analysis.get('fun_fact', 'Enjoys coding!')}</p>
        </div>
    </body>
    </html>
    """
    return html

@mcp.tool()
async def save_card(username: str, html: str) -> str:
    """Save the generated HTML card to the static directory."""
    print(f"DEBUG: Saving card for {username}")
    file_path = f"static/cards/{username}.html"
    full_path = os.path.join(os.path.dirname(__file__), file_path)
    
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return f"/static/cards/{username}.html"

if __name__ == "__main__":
    mcp.run()
