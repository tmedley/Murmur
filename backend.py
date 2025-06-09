# backend.py
#
# Murmur
# a universal AI chat app for macOS
# Tim Medley tim@medley.us
#
# Backend AI Chat service API access


import os
from abc import ABC, abstractmethod

try:
    import openai
    from openai import OpenAI
except ModuleNotFoundError:
    openai = None
    OpenAI = None


def get_openai_models(api_key):
    if not openai:
        print("OpenAI module not loaded.")
        return []

    print(f"Fetching models using API key: {api_key[:8]}...")

    openai.api_key = api_key
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.models.list()
        models = [m.id for m in response.data]
        print(f"Found models: {models}")
        return models
    except Exception as e:
        print(f"Error fetching OpenAI models: {e}")
        return []

def get_claude_models(api_key):
    # Your API call logic here
    return ["claude-3-opus", "claude-3-sonnet"]

def get_gemini_models(api_key):
    # Your API call logic here
    return ["gemini-1.5-pro", "gemini-1.5-flash"]


class ChatClient(ABC):
    @abstractmethod
    def send_message(self, prompt: str) -> str:
        pass

class OpenAIClient(ChatClient):
    def __init__(self, api_key: str):
        self.api_key = api_key
        if openai:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def send_message(self, prompt: str, model: str) -> str:
        print(f"[OpenAIClient.send_message] Prompt: {prompt}")
        print(f"[OpenAIClient.send_message] Model from dropdown: {model}")
        print(f"[OpenAIClient.send_message] API Key (masked): {self.api_key[:8]}...")
    
        if not self.client:
            print("[OpenAIClient.send_message] Error: OpenAI client not available.")
            return "Error: OpenAI client not available."
        try:
            print(f"[OpenAIClient.send_message] Preparing to call client.chat.completions.create with model '{model}'")
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                timeout=10,
            )
            print("[OpenAIClient.send_message] Successfully received response from OpenAI.")
            return response.choices[0].message.content.strip()
        except openai.APIConnectionError as e:
            print(f"[OpenAIClient.send_message] OpenAI API Connection Error: {e}")
            return f"[Error connecting to OpenAI API: {e}]"
        except openai.APIStatusError as e:
            # Use .response.json() for more detail if available, or .text
            print(f"[OpenAIClient.send_message] OpenAI API Status Error: {e.status_code} - {e.response.text}")
            return f"[Error from OpenAI API (Status {e.status_code}): {e.response.text}]"
        except Exception as e:
            print(f"[OpenAIClient.send_message] Generic Error during OpenAI chat: {e}")
            return f"[Error from OpenAI: {e}]"

class ClaudeClient(ChatClient):
    def send_message(self, prompt: str) -> str:
        return "Claude response simulation (not implemented)"

class GeminiClient(ChatClient):
    def send_message(self, prompt: str) -> str:
        return "Gemini response simulation (not implemented)"

class ChatService:
    def __init__(self, provider, api_key=""):
        self.provider = provider
        self.api_key = api_key

    def get_client(self, provider: str) -> ChatClient:
        if provider.lower() == "openai":
            return OpenAIClient(api_key=self.api_key)
        elif provider.lower() == "claude":
            return ClaudeClient()
        elif provider.lower() == "gemini":
            return GeminiClient()
        else:
            raise ValueError("Unsupported provider")