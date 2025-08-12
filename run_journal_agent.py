#!/usr/bin/env python3
"""
Direct entry point for the Journaling Assistant Agent.
"""
import asyncio
import sys
import os

# Add the src/journaling_assistant directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'journaling_assistant'))

from agent import main as agent_main

if __name__ == "__main__":
    asyncio.run(agent_main())