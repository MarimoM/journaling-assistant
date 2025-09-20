#!/usr/bin/env python3
"""
Synchronous wrapper for the Journaling Assistant to work with Streamlit.
"""

import asyncio
import nest_asyncio
from typing import Optional, List
from .agent import JournalingAssistant as AsyncJournalingAssistant, JournalingContext

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

class SyncJournalingAssistant:
    """Synchronous wrapper for the journaling assistant."""
    
    def __init__(self, user_name: Optional[str] = None):
        """Initialize the synchronous journaling assistant."""
        self.async_assistant = AsyncJournalingAssistant(user_name)
    
    def chat(self, message: str, stream: bool = False) -> str:
        """Send a message to the agent and get a response synchronously."""
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async method
            return loop.run_until_complete(
                self.async_assistant.chat(message, stream=stream)
            )
        except Exception as e:
            return f"Error: {str(e)}"
    
    def set_mood(self, mood: str):
        """Set the current mood."""
        self.async_assistant.set_mood(mood)
    
    def add_goal(self, goal: str):
        """Add a goal."""
        self.async_assistant.add_goal(goal)
    
    def get_context(self) -> JournalingContext:
        """Get the current context."""
        return self.async_assistant.get_context()
    
    @property
    def context(self) -> JournalingContext:
        """Get the context."""
        return self.async_assistant.context