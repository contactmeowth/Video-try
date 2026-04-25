#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests
import re

SYSTEM_PROMPT = """
You are a creative video script writer for a Manhwa Recap channel. Given a topic/chapter, generate a JSON script for an AI video pipeline. 

The JSON must follow this EXACT structure:
{
  "title": "Short title",
  "output_filename": "recap_video.mp4",
  "resolution": "1280x720",
  "default_voice": "af_heart",
  "scenes": [
    {
      "id": 1,
      "type": "ai_image",
      "image_prompt": "Cinematic Manhwa style art, detailed visual description",
      "narration": "Full narration text for this scene. Make it sound like a dramatic storyteller.",
      "voice": "af_heart",
      "mood": "epic",
      "transition": "fade"
    }
  ]
}

Rules:
- Generate ONLY valid JSON, no markdown formatting (no ```json).
- Narration should summarize the story dramatically (3-5 sentences per scene).
- ONLY use these specific Kokoro voices: 'af_heart' (female narrator), 'af_bella', 'am_adam' (male narrator), 'am_michael'. Do NOT use any other voices.
- Make the image prompts 'Manhwa/Webtoon style, cinematic lighting, highly detailed'.
"""

def generate_script(story_idea: str, num_scenes: int = 15) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Set GEMINI_API_KEY environment variable")
        sys.exit(1)

    # Clean the API key just in case there are hidden spaces/newlines from GitHub Secrets
    api_key = api_key.strip()

    prompt = (
        f"Topic/Chapters to cover: {story_idea}\n\n"
        f"Generate exactly {num_scenes} scenes for a Manhwa recap video.\n"
    )

    print("🧠 Fetching script from Gemini via REST API...")
    
    # URL ko split kar diya taaki GitHub editor isko auto-format na kar paye
    base_url = "https://" + "generativelanguage.googleapis.com"
    endpoint = "/v1beta/models/gemini-2.0-flash:generateContent?key="
    url = base_url + endpoint + api_key
    
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8}
    }

    try:
        res = requests.post(url, json=payload, timeout=90).json()
        
        if 'error' in res:
            err_msg = res['error'].get('message', 'Unknown Error')
            raise Exception(f"API_ERROR: {err_msg}")
            
        text = res['candidates'][0]['content']['parts'][0]['text']
        
        # Clean JSON
        clean = re.sub(r'```json\s*|\s*```', '', text).strip()
        
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', clean)
            if match:
                return json.loads(match.group())
            raise Exception("JSON_PARSE_FAILED")

    except Exception as e:
        print(f"❌ Failed to get script from Gemini: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("idea", help="Story idea")
    parser.add_argument("--scenes", type=int, default=15)
    args = parser.parse_args()
    
    script = generate_script(args.idea, args.scenes)
    
    with open("script.json", "w") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
