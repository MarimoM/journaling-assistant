#!/usr/bin/env python3
"""
Simple chat interface using the Pydantic AI Journaling Agent.
"""
import asyncio
import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import JournalingAssistant

async def main():
    if len(sys.argv) > 1:
        prompt = ' '.join(sys.argv[1:])
        
        print(f"\n💭 You: {prompt}")
        print("-" * 50)
        print("🤖 Assistant: ", end='')
        
        assistant = JournalingAssistant()
        # Use non-streaming for now to avoid hanging
        response = await assistant.chat(prompt, stream=False)
        print(response)
    else:
        # Interactive mode - use the full agent interface
        from agent import main as agent_main
        await agent_main()

if __name__ == "__main__":
    asyncio.run(main())