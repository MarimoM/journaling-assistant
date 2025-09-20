#!/usr/bin/env python3
"""
Conversation summarizer for generating meaningful titles from journaling conversations.
"""

from typing import List, Dict, Any, Optional
from .ollama_model import OllamaModel
from .template_manager import template_manager
from .database import Message

class ConversationSummarizer:
    """Generates meaningful summaries and titles for journaling conversations."""
    
    def __init__(self, model_name: str = 'llama3:latest'):
        """Initialize the summarizer with an Ollama model."""
        self.model = OllamaModel(model_name)
    
    async def generate_title(self, messages: List[Message]) -> str:
        """Generate a meaningful title for a conversation based on the first message."""
        if not messages:
            return "Empty conversation"
        
        # Get the first user message
        first_user_msg = next((msg for msg in messages if msg.role == "user"), None)
        if not first_user_msg:
            return "No user message found"
        
        # For very short messages, just clean them up
        if len(first_user_msg.content) <= 60:
            return first_user_msg.content.strip()
        
        # For longer messages, use LLM to generate a concise summary
        try:
            # Create a simple summarization prompt for just the first message
            summary_prompt = f"""Create a concise, meaningful title (3-8 words) for a journaling conversation that begins with this message:

"{first_user_msg.content}"

The title should capture the main theme or emotion. Examples:
- "Processing work stress and anxiety"
- "Reflecting on relationship challenges"
- "Celebrating personal achievements"
- "Exploring career transition fears"

Respond with ONLY the title, no quotes or additional text."""
            
            # Create a mock request structure for the model
            class MockPart:
                def __init__(self, content):
                    self.content = content
            
            class MockMessage:
                def __init__(self, parts):
                    self.parts = parts
            
            mock_message = MockMessage([MockPart(summary_prompt)])
            mock_request = [mock_message]
            
            # Get the title from the model
            response = await self.model.request(mock_request)
            
            if response and response.parts:
                title = response.parts[0].content.strip()
                # Clean up the response - remove quotes, extra whitespace
                title = title.strip('"\'').strip()
                
                # Ensure reasonable length
                if len(title) > 60:
                    title = title[:57] + "..."
                
                return title if title else "Untitled conversation"
            else:
                return "Conversation summary unavailable"
                
        except Exception as e:
            print(f"Error generating title: {e}")
            # Fallback to truncated first message
            content = first_user_msg.content[:50].strip()
            if len(first_user_msg.content) > 50:
                content += "..."
            return content
    
    def generate_title_sync(self, messages: List[Message]) -> str:
        """Synchronous wrapper for title generation."""
        import asyncio
        import nest_asyncio
        
        try:
            # Apply nest_asyncio to handle nested event loops
            nest_asyncio.apply()
            
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async method
            return loop.run_until_complete(self.generate_title(messages))
        except Exception as e:
            print(f"Error in sync title generation: {e}")
            # Fallback to first user message
            if messages:
                first_user_msg = next((msg for msg in messages if msg.role == "user"), None)
                if first_user_msg:
                    content = first_user_msg.content[:50].strip()
                    if len(first_user_msg.content) > 50:
                        content += "..."
                    return content
            return "Untitled conversation"

# Global summarizer instance
summarizer = ConversationSummarizer()