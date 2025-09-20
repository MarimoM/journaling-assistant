# file: ollama_model.py

import httpx
import json
from typing import Any, AsyncIterator
from pydantic_ai.models import Model, ModelResponse, ModelRequest, StreamedResponse
from pydantic_ai.messages import (
    SystemPromptPart,
    UserPromptPart,
    ToolCallPart,
    ToolReturnPart,
    TextPart
)

import langfuse


OLLAMA_API_URL = "http://localhost:11434/api/chat"


class OllamaModel(Model):
    """Custom Ollama model that supports tool calling via the REST API."""

    def __init__(self, model_name: str = 'llama3:latest'):
        self._model_name = model_name
        self._system_prompt = ""
        self._agent_system_prompt = ""  # Store system prompt from agent

    def model_name(self) -> str:
        return self._model_name

    async def system(self, system_prompt: str) -> None:
        """Store the system prompt to be included in requests."""
        self._system_prompt = system_prompt

    async def request(self, messages, model_settings=None, model_request_parameters=None) -> ModelResponse:
        """Make a structured request to the Ollama /api/chat endpoint."""

        print(f"DEBUG: OllamaModel.request called with {len(messages)} messages")
        print(f"DEBUG: self._system_prompt: {self._system_prompt[:100] if self._system_prompt else 'None'}")
        print(f"DEBUG: model_request_parameters: {model_request_parameters}")

        messages_from_args = messages
        tools = getattr(model_request_parameters, 'function_tools', []) if model_request_parameters else []

        # Check if system prompt is in model_request_parameters
        system_prompt = getattr(model_request_parameters, 'system_prompt', None) if model_request_parameters else None
        if system_prompt:
            print(f"DEBUG: Found system prompt in parameters: {system_prompt[:100]}...")
            self._system_prompt = system_prompt

        ollama_messages = []

        # Add system prompt if available (prefer agent system prompt)
        system_prompt_to_use = self._agent_system_prompt or self._system_prompt
        if system_prompt_to_use:
            print(f"DEBUG: Using system prompt: {system_prompt_to_use[:100]}...")
            ollama_messages.append({"role": "system", "content": system_prompt_to_use})

        for message in messages_from_args:
            print(f"DEBUG: Processing message: {message.__class__.__name__}")
            print(f"DEBUG: Message parts: {[part.__class__.__name__ for part in message.parts]}")

            if hasattr(message, '__class__'):
                if 'Request' in message.__class__.__name__:
                    message_role = "user"
                elif 'Response' in message.__class__.__name__:
                    message_role = "assistant"
                else:
                    message_role = "user"  # default fallback
            else:
                message_role = "user"

            for part in message.parts:
                print(f"DEBUG: Processing part: {part.__class__.__name__}, content preview: {str(part)[:100]}")
                if isinstance(part, UserPromptPart) or isinstance(part, TextPart):
                    ollama_messages.append({"role": message_role, "content": part.content})
                elif isinstance(part, SystemPromptPart):
                    print(f"DEBUG: Found SystemPromptPart!")
                    ollama_messages.append({"role": "system", "content": part.content})
                elif isinstance(part, ToolReturnPart):
                    print(f"DEBUG: Found ToolReturnPart! Content: {part.content[:100]}...")
                    # Tool returns are sent as 'tool' role in Ollama format
                    ollama_messages.append({
                        "role": "tool",
                        "content": part.content,
                        "tool_call_id": part.tool_call_id
                    })
                elif isinstance(part, ToolCallPart):
                    print(f"DEBUG: Found ToolCallPart!")
                    # Tool calls from assistant need to be formatted properly for Ollama
                    if message_role == "assistant":
                        # Create assistant message with tool calls
                        ollama_messages.append({
                            "role": "assistant",
                            "content": "",  # Empty content when making tool calls
                            "tool_calls": [{
                                "id": part.tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": part.tool_name,
                                    "arguments": part.args
                                }
                            }]
                        })

        ollama_tools = []
        for tool in tools:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_json_schema
                }
            })

        payload = {
            "model": self._model_name,
            "messages": ollama_messages,
            "stream": False
        }

        if ollama_tools:
            payload["tools"] = ollama_tools

        client = langfuse.get_client()
        try:
            print(f"DEBUG: ollama_messages being sent to Langfuse: {ollama_messages}")

            with client.start_as_current_generation(
                name="ollama-request",
                model=self._model_name,
                input=ollama_messages
            ) as generation:

                async with httpx.AsyncClient(timeout=120.0) as http_client:
                    response = await http_client.post(OLLAMA_API_URL, json=payload)
                    response_data = response.json()

                response_message = response_data.get("message", {})

                if response_message.get("tool_calls"):
                    print('DEBUG: the tool was called', response_message.get("tool_calls"))
                    tool_calls = []
                    for tc in response_message["tool_calls"]:
                        tool_id = tc.get("id", f"call_{tc.get('function', {}).get('name', 'unknown')}")
                        tool_name = tc.get("function", {}).get("name", "unknown")
                        tool_args = tc.get("function", {}).get("arguments", {})

                        if isinstance(tool_args, str):
                            try:
                                tool_args = json.loads(tool_args)
                            except:
                                tool_args = {}

                        tool_calls.append(
                            ToolCallPart(
                                tool_name=tool_name,
                                args=tool_args,
                                tool_call_id=tool_id
                            )
                        )
                    return ModelResponse(parts=tool_calls)
                else:
                    content = response_message.get("content", "")
                    return ModelResponse(parts=[TextPart(content=content)])

        except Exception as e:
            raise Exception(f"An unexpected error occurred: {str(e)}")

    async def request_stream(self, *args: Any, **kwargs: Any) -> AsyncIterator[StreamedResponse]:
        """Streaming is not fully implemented for this example."""
        response = await self.request(*args, **kwargs)
        for part in response.parts:
            if isinstance(part, TextPart):
                yield StreamedResponse(delta=part.content)
