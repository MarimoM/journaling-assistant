#!/usr/bin/env python3
"""
Pydantic AI Agent for Journaling Assistant.
"""

import asyncio
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, UsageLimits
from .ollama_model import OllamaModel
from .template_manager import template_manager
from langfuse import get_client, observe
from pydantic_ai.models import ModelRequest
from pydantic_ai.messages import UserPromptPart

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

# mistral:latest
# llama3.1
# llama3.1:8b?
llama_model = OllamaModel(model_name='llama3.1:8b')
tool_model = OllamaModel(model_name='llama3.1:8b')

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
    return template_manager.render_template('system_prompt.j2', {'user_context': user_context})

@observe(name="analyze_sentiment_tool")
async def analyze_sentiment(ctx: RunContext[JournalingContext], request: str) -> str:
    """Analyze the emotional state and sentiment based on the current conversation.
    Call this ONLY when the user explicitly asks about their mood, emotions, or mental state."""
    #
    # print(f"DEBUG: analyze_sentiment called with request: '{request}'")
    # try:
    #     sentiment_prompt = template_manager.render_template('sentiment_analysis.j2')
    #
    #     result = await tool_model.request([
    #         ModelRequest(parts=[UserPromptPart(content=sentiment_prompt)])
    #     ])
    #
    #     if hasattr(result, 'parts') and result.parts:
    #         return result.parts[0].content
    #     else:
    #         return "Cannot analyze"
    #
    # except Exception as e:
    #     print(f"Error in sentiment analysis: {e}")
    #     return "Request failed, try again later."
    return "RETURN THE MESSAGE TO A CLIENT THAT HEY ARE HAPPY. DO NOT CALL ANY MORE TOOLS."

@observe(name="summarize_chat_tool")
async def summarize_chat(ctx: RunContext[JournalingContext], request: str = "summarize conversation") -> str:
    """
    Summarize the chat content, highlighting key points.
    RULE: Only call this tool if the user explicitly asks for a summary and the conversation has more than 3 messages.
    NEVER call this tool for simple greetings like 'hello' or initial messages.
    """
    print(f"TOOL CALLED: summarize_chat with request: {request}")
    #
    # try:
    #     summary_prompt = template_manager.render_template('chat_summary.j2')
    #     print(f"DEBUG: Using chat_summary.j2 template")
    #
    #     result = await tool_model.request([
    #         ModelRequest(parts=[UserPromptPart(content=summary_prompt)])
    #     ])
    #
    #     if hasattr(result, 'parts') and result.parts:
    #         summary_result = result.parts[0].content
    #         print(f"DEBUG: Chat summary completed successfully")
    #
    #         final_instructional_output = f"""
    #             The user requested a summary of our conversation. I have generated it. Here is the summary:
    #             ---
    #             {summary_result}
    #             ---
    #             Your task is now to present this summary to the user in a helpful and conversational tone.
    #             Do not call any more tools. Formulate a final response based on this summary.
    #             """
    #         return final_instructional_output
    #     else:
    #         return "Failed."
    #
    # except Exception as e:
    #     print(f"Error in chat summary: {e}")
    #     return "I had trouble creating the summary. Let's try again in a bit."
    return "RETURN THE MESSAGE TO A CLIENT THAT CONVERSATION JUST STARTED. DO NOT CALL ANY MORE TOOLS."

@observe
async def run_journaling_agent(message: str, context: JournalingContext, message_history: List = None) -> str:
    """Run the journaling agent with the given message and context."""
    system_prompt = get_dynamic_system_prompt(context)
    print(f"DEBUG: System prompt length: {len(system_prompt)}")
    print(f"DEBUG: System prompt preview: {system_prompt[:200]}...")

    # Manually set the system prompt on the model since pydantic-ai doesn't pass it automatically
    llama_model._agent_system_prompt = system_prompt

    # Only enable tools for specific requests to prevent infinite loops
    should_enable_tools = any(phrase in message.lower() for phrase in [
        "analyze my mood", "summarize our conversation", "what are the key points", "recap", "summary"
    ])

    agent_config = {
        "model": llama_model,
        "output_type": str,
        "system_prompt": system_prompt,
    }

    if should_enable_tools:
        print(f"DEBUG: Enabling tools for message: {message}")
        agent_config["tools"] = [analyze_sentiment, summarize_chat]
    else:
        print(f"DEBUG: No tools enabled for message: {message}")

    agent = Agent(**agent_config)

    try:
        print(f"DEBUG: Starting agent.run with message: '{message[:50]}...'")
        print(f"DEBUG: Message history length: {len(message_history or [])}")

        result = await agent.run(
            message,
            message_history=message_history or [],
            deps=context,
            usage_limits=UsageLimits(request_limit=10)  # Reasonable limit for tool completion
        )
        print(f"DEBUG: Agent.run completed successfully")
        return result.output
    except Exception as e:
        print(f"DEBUG: Agent.run failed with error: {e}")
        print(f"DEBUG: Error type: {type(e)}")
        raise

@observe(name="chat_with_agent")
async def chat_with_agent(
        message: str,
        context: JournalingContext,
) -> str:
    """Chat with the journaling agent."""

    client = get_client()

    from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

    message_history = []
    for msg in context.conversation_history:
        if msg["role"] == "user":
            message_history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
        elif msg["role"] == "assistant":
            message_history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))

    response_text = await run_journaling_agent(message, context, message_history)

    client.update_current_span(
        input=message,
        output=response_text,
        metadata={
            "response_length": len(response_text),
            "status": "success",
        }
    )

    return response_text

class JournalingAssistant:
    """Main journaling assistant class."""

    def __init__(self, user_name: Optional[str] = None):
        self.context = JournalingContext(
            user_name=user_name,
            session_id=f"session_{asyncio.get_event_loop().time()}"
        )

    @observe(name="journaling_chat")
    async def chat(self, message: str, stream: bool = False) -> str:
        """Send a message to the agent and get a response."""

        client = get_client()

        try:
            self.context.conversation_history.append({"role": "user", "content": message})
            response = await chat_with_agent(message, self.context)
            self.context.conversation_history.append({"role": "assistant", "content": response})
            client.update_current_span(
                input=message,
                output=response,
                metadata={
                    "response_generated": True,
                    "final_conversation_length": len(self.context.conversation_history)
                }
            )

            return response
        except Exception as e:
            client.update_current_span(
                input=message,
                output=f"Error: {str(e)}",
                metadata={
                    "error": str(e),
                    "response_generated": False
                }
            )
            raise
