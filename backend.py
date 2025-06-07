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

class ChatClient(ABC):
    @abstractmethod
    def send_message(self, prompt: str) -> str:
        pass

class OpenAIClient(ChatClient):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if OpenAI:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def send_message(self, prompt: str) -> str:
        if not self.client:
            return "Error: OpenAI client not available."
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

class ClaudeClient(ChatClient):
    def send_message(self, prompt: str) -> str:
        return "Claude response simulation (not implemented)"

class GeminiClient(ChatClient):
    def send_message(self, prompt: str) -> str:
        return "Gemini response simulation (not implemented)"

class ChatService:
    def __init__(self, provider: str):
        self.client = self.get_client(provider)

    def get_client(self, provider: str) -> ChatClient:
        if provider == "openai":
            return OpenAIClient()
        elif provider == "claude":
            return ClaudeClient()
        elif provider == "gemini":
            return GeminiClient()
        else:
            raise ValueError("Unsupported provider")

    def chat(self, prompt: str) -> str:
        return self.client.send_message(prompt)