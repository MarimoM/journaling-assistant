#!/usr/bin/env python3
"""
Custom Ollama model implementation for pydantic-ai.
"""

import asyncio
import subprocess
import json
from typing import List, Dict, Any, Optional, Union, AsyncIterator
from pydantic_ai.models import Model, ModelResponse, ModelRequest, StreamedResponse
from pydantic_ai.messages import ModelMessage, SystemPromptPart, UserPromptPart, TextPart


class OllamaModel(Model):
    """Custom Ollama model implementation for pydantic-ai."""
    
    def __init__(self, model_name: str = 'llama3:latest'):
        self._model_name = model_name
    
    def model_name(self) -> str:
        """Return the model name."""
        return self._model_name
    
    async def system(self, system_prompt: str) -> None:
        """Handle system prompt - Ollama handles this within the conversation."""
        # Ollama handles system prompts as part of the conversation
        # We'll store it and include it in the request
        self._system_prompt = system_prompt
    
    async def request(
        self,
        *args,
        **kwargs: Any
    ) -> ModelResponse:
        """Make a request to the Ollama model."""
        
        # Extract the messages from args (first arg is the messages list)
        messages = args[0] if args else []
        if not messages:
            raise Exception("No messages provided")
        
        # Simple approach: extract the last user message and system prompts
        user_message = ""
        system_prompt_text = ""
        
        # Extract user messages and system prompts from ModelRequest parts
        for message in messages:
            if hasattr(message, 'parts'):
                for part in message.parts:
                    if isinstance(part, SystemPromptPart):
                        system_prompt_text += part.content + "\n"
                    elif isinstance(part, UserPromptPart):
                        user_message = part.content
                    elif hasattr(part, 'content'):
                        user_message = part.content
        
        # Build final prompt
        if system_prompt_text:
            final_prompt = f"{system_prompt_text}\n\nUser: {user_message}\n\nAssistant:"
        else:
            final_prompt = user_message
        
        try:
            # Use synchronous subprocess for simplicity
            result = subprocess.run(
                ['ollama', 'run', self._model_name, final_prompt],
                capture_output=True,
                text=True,
                check=True
            )
            
            response_text = result.stdout.strip()
            
            # Create ModelResponse with TextPart
            text_part = TextPart(content=response_text)
            return ModelResponse(
                parts=[text_part]
            )
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Ollama request failed: {e}")
        except FileNotFoundError:
            raise Exception("Ollama not found. Make sure Ollama is installed and running.")
        except Exception as e:
            raise Exception(f"Error calling Ollama: {str(e)}")
    
    async def request_stream(
        self,
        request: ModelRequest,
        **kwargs: Any
    ) -> AsyncIterator[StreamedResponse]:
        """Stream response from Ollama model."""
        # For now, implement as non-streaming
        response = await self.request(request, **kwargs)
        yield StreamedResponse(delta=response.response)