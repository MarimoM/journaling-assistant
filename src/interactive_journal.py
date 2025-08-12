#!/usr/bin/env python3
"""
Simple interactive journaling assistant.
"""
import asyncio
import sys
import os

# Add the journaling_assistant directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'journaling_assistant'))

from agent import JournalingAssistant

async def main():
    print("🌟 Welcome to your Journaling Assistant powered by Llama 3! 🌟")
    print("Type 'quit' to exit, 'mood <your_mood>' to set mood, or 'goal <your_goal>' to add a goal.\n")
    
    user_name = input("What's your name? (optional): ").strip()
    if not user_name:
        user_name = None
    
    assistant = JournalingAssistant(user_name)
    
    while True:
        try:
            user_input = input("\n💭 You: ").strip()
            
            if user_input.lower() == 'quit':
                print("Thank you for journaling today. Take care! 🌸")
                break
            
            if user_input.lower().startswith('mood '):
                mood = user_input[5:].strip()
                assistant.set_mood(mood)
                print(f"✨ Mood set to: {mood}")
                continue
            
            if user_input.lower().startswith('goal '):
                goal = user_input[5:].strip()
                assistant.add_goal(goal)
                print(f"🎯 Goal added: {goal}")
                continue
            
            if not user_input:
                continue
            
            print("🤖 Assistant: ", end='')
            # Use non-streaming for reliability
            response = await assistant.chat(user_input, stream=False)
            print(response)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! Take care! 👋")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(main())