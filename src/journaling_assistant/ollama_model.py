#!/usr/bin/env python3
"""
Custom Ollama model implementation for pydantic-ai with Langfuse integration.
"""

import asyncio
import subprocess
import json
import time
from typing import List, Dict, Any, Optional, Union, AsyncIterator
from pydantic_ai.models import Model, ModelResponse, ModelRequest, StreamedResponse
from pydantic_ai.messages import ModelMessage, SystemPromptPart, UserPromptPart, TextPart
from langfuse import observe, get_client
import langfuse


class OllamaModel(Model):
    """Custom Ollama model implementation for pydantic-ai with Langfuse tracking."""
    
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
    
    @observe(name="ollama_request")
    async def request(
        self,
        *args,
        **kwargs: Any
    ) -> ModelResponse:
        """Make a request to the Ollama model with Langfuse tracking."""

        client = get_client()
        
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
            process = subprocess.Popen(
                ['ollama', 'run', self._model_name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Use stdin to avoid command line length limits and escaping issues
            with client.start_as_current_generation(
                name="llm-response", 
                model=self._model_name,
                input=final_prompt,
                metadata={
                    "user_message": user_message,
                    "system_prompt": system_prompt_text,
                    "model_provider": "ollama"
                }
            ) as generation:
                stdout, stderr = process.communicate(input=final_prompt)

                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, 'ollama run', stderr)

                response_text = stdout.strip()

                # Update generation with the response
                generation.update(
                    output=response_text,
                    usage={
                        "input": len(final_prompt.split()),
                        "output": len(response_text.split()),
                        "total": len(final_prompt.split()) + len(response_text.split())
                    }
                )

                # Create ModelResponse with TextPart
                text_part = TextPart(content=response_text)
                return ModelResponse(parts=[text_part])
            
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