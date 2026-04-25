import os
import subprocess
from story_to_script import generate_script
import json

def run_automation():
    # 1. Read the topic
    if not os.path.exists("topic.txt"):
        print("❌ topic.txt not found! Please create it and write your topic.")
        return

    with open("topic.txt", "r") as f:
        topic = f.read().strip()

    if not topic:
        print("⚠️ topic.txt is empty. Skipping...")
        return

    print(f"🚀 Starting Automation for topic: {topic}")

    # 2. Generate script using Gemini
    # Generating 15 scenes for a decent length video
    print("🧠 Asking Gemini to write the script...")
    script_data = generate_script(topic, num_scenes=15)
    
    with open("script.json", "w") as f:
        json.dump(script_data, f, indent=2, ensure_ascii=False)
    
    print("✅ script.json generated automatically.")

    # 3. Run the Video Pipeline
    print("🎬 Starting video generation pipeline...")
    subprocess.run(["python", "generate_video.py", "script.json"], check=True)

if __name__ == "__main__":
    run_automation()
