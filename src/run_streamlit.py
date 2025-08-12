#!/usr/bin/env python3
"""
Launcher script for the Streamlit Journaling Assistant.
"""
import subprocess
import sys
import os

def main():
    """Launch the Streamlit app."""
    app_path = os.path.join(os.path.dirname(__file__), 'streamlit_app.py')
    
    cmd = [
        'pixi', 'run', 'streamlit', 'run', app_path,
        '--server.headless', 'false',
        '--server.runOnSave', 'true',
        '--theme.base', 'light'
    ]
    
    print("🌟 Starting Journaling Assistant UI...")
    print("📱 The app will open in your default browser")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Goodbye! Thanks for journaling!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting Streamlit: {e}")
        print("Make sure you're in the project directory and Ollama is running.")

if __name__ == "__main__":
    main()