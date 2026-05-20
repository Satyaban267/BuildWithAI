import asyncio
import os
import json
from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card
from dotenv import load_dotenv

load_dotenv()

async def test_end_to_end():
    username = "torvalds"
    print(f"--- Testing end-to-end for {username} ---")
    
    try:
        # 1. Scrape GitHub
        print("1. Calling scrape_github...")
        github_data = await scrape_github(username)
        print("   Success!")

        # 2. Analyze Profile
        print("2. Calling analyze_profile...")
        analysis = await analyze_profile(github_data)
        print("   Success!")

        # 3. Generate HTML Card
        print("3. Calling generate_card_html...")
        html_card = await generate_card_html(username, github_data, analysis)
        print("   Success!")

        # 4. Print results
        print("\n--- Results ---")
        print(f"Card Theme: {analysis.get('card_theme')}")
        print(f"Developer Vibe: {analysis.get('developer_vibe')}")
        
    except Exception as e:
        print(f"\n[!] Tool failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
