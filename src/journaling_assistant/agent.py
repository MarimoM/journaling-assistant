#!/usr/bin/env python3
"""
Pydantic AI Agent for Journaling Assistant using Llama 3 model via Ollama.
"""

import asyncio
import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from ollama_model import OllamaModel
from template_manager import template_manager
from langfuse import get_client, observe

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class JournalingContext(BaseModel):
    """Context for journaling sessions."""
    user_name: Optional[str] = None
    session_id: str
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    current_mood: Optional[str] = None
    goals: List[str] = Field(default_factory=list)

class JournalEntry(BaseModel):
    """Structure for journal entries."""
    title: str
    content: str
    mood: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    insights: Optional[str] = None

# Initialize the Ollama model
llama_model = OllamaModel(model_name='llama3:latest')

# Create the Pydantic AI agent with dynamic system prompt
def get_dynamic_system_prompt(context: Optional[JournalingContext] = None) -> str:
    """Generate system prompt with context."""
    user_context = None
    if context:
        user_context = {
            "user_name": context.user_name,
            "current_mood": context.current_mood,
            "goals": context.goals,
            "conversation_history": context.conversation_history
        }
    
    return template_manager.render_system_prompt(user_context)

# Initialize with base system prompt
journaling_agent = Agent(
    model=llama_model,
    result_type=str,
    system_prompt=get_dynamic_system_prompt(),
)

@journaling_agent.system_prompt
def add_context_to_prompt(ctx: RunContext[JournalingContext]) -> str:
    """Add dynamic context to the system prompt using templates."""
    # Render the full system prompt with current context
    user_context = {
        "user_name": ctx.deps.user_name,
        "current_mood": ctx.deps.current_mood,
        "goals": ctx.deps.goals,
        "conversation_history": ctx.deps.conversation_history
    }
    
    # Return the rendered template as the complete system prompt
    return template_manager.render_system_prompt(user_context)

@journaling_agent.tool
def save_journal_entry(ctx: RunContext[JournalingContext], entry: JournalEntry) -> str:
    """Save a journal entry (placeholder implementation)."""
    print(f"\n--- Journal Entry Saved ---")
    print(f"Title: {entry.title}")
    print(f"Content: {entry.content}")
    if entry.mood:
        print(f"Mood: {entry.mood}")
    if entry.tags:
        print(f"Tags: {', '.join(entry.tags)}")
    if entry.insights:
        print(f"Insights: {entry.insights}")
    print("--- End Entry ---\n")
    
    return f"Journal entry '{entry.title}' has been saved successfully."

@journaling_agent.tool
def update_mood(ctx: RunContext[JournalingContext], mood: str) -> str:
    """Update the user's current mood."""
    ctx.deps.current_mood = mood
    return f"Mood updated to: {mood}"

@journaling_agent.tool
def add_goal(ctx: RunContext[JournalingContext], goal: str) -> str:
    """Add a new goal for the user."""
    ctx.deps.goals.append(goal)
    return f"Goal added: {goal}"

@observe(name="chat_with_agent")
async def chat_with_agent(
    message: str,
    context: JournalingContext,
    stream: bool = False
) -> str:
    """Chat with the journaling agent."""
    
    # Get the Langfuse client for trace creation
    client = get_client()
    
    try:
        # Always use non-streaming for now due to Ollama model limitations
        result = await journaling_agent.run(message, deps=context)
        response_text = result.data
        
        # Update span with success
        client.update_current_span(
            input=message,
            output=response_text,
            metadata={
                "response_length": len(response_text),
                "status": "success"
            }
        )
        
        if stream:
            # Simulate streaming by printing character by character
            for char in response_text:
                print(char, end='', flush=True)
                await asyncio.sleep(0.01)  # Small delay for streaming effect
            print()  # New line after streaming
        
        return response_text
    except Exception as e:
        # Update span with error
        client.update_current_span(
            input=message,
            output=f"Error: {str(e)}",
            metadata={
                "status": "error",
                "error": str(e)
            }
        )
        return f"Error: {str(e)}"

class JournalingAssistant:
    """Main journaling assistant class."""
    
    def __init__(self, user_name: Optional[str] = None):
        self.context = JournalingContext(
            user_name=user_name,
            session_id=f"session_{asyncio.get_event_loop().time()}"
        )
    
    @observe(name="journaling_chat")
    async def chat(self, message: str, stream: bool = True) -> str:
        """Send a message to the agent and get a response."""
        
        # Get the Langfuse client for trace creation
        client = get_client()
        
        try:
            # Add to conversation history
            self.context.conversation_history.append({"role": "user", "content": message})
            response = await chat_with_agent(message, self.context, stream=stream)
            self.context.conversation_history.append({"role": "assistant", "content": response})
            client.update_current_span(
                input=message,
                output=response,
                metadata={
                    "response_generated": True,
                    "final_conversation_length": len(self.context.conversation_history),
                    "has_mood": self.context.current_mood is not None,
                    "goals_count": len(self.context.goals)
                }
            )
            
            return response
        except Exception as e:
            # Update span with error
            client.update_current_span(
                input=message,
                output=f"Error: {str(e)}",
                metadata={
                    "error": str(e),
                    "response_generated": False
                }
            )
            raise
    
    def set_mood(self, mood: str):
        """Set the current mood."""
        self.context.current_mood = mood
    
    def add_goal(self, goal: str):
        """Add a goal."""
        self.context.goals.append(goal)
    
    def get_context(self) -> JournalingContext:
        """Get the current context."""
        return self.context

async def main():
    """Interactive journaling session."""
    print("🌟 Welcome to your Journaling Assistant powered by Llama 3! 🌟")
    print("Type 'quit' to exit, 'mood <your_mood>' to set mood, or 'goal <your_goal>' to add a goal.\n")
    
    user_name = input("What's your name? (optional): ").strip()
    if not user_name:
        user_name = None
    
    assistant = JournalingAssistant(user_name)
    
    try:
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
                await assistant.chat(user_input, stream=True)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! Take care! 👋")
                break
            except Exception as e:
                print(f"\nError: {e}")
    finally:
        # Flush Langfuse events before exiting
        langfuse = get_client()
        langfuse.flush()

if __name__ == "__main__":
    asyncio.run(main())