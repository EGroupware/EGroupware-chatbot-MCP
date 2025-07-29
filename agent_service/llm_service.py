import os
import openai
from dotenv import load_dotenv
from enum import Enum, auto
from typing import Optional, Dict, Any, List

load_dotenv()

class ProviderType(Enum):
    OPENAI = "openai"
    IONOS = "ionos"
    GITHUB = "github"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"
    AZURE = "azure"

class Provider:
    """Base class for AI model providers"""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url

    def get_client(self):
        raise NotImplementedError("Subclasses must implement get_client method")

    def get_completion(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], stream: bool = True):
        raise NotImplementedError("Subclasses must implement get_completion method")

    @staticmethod
    def create_provider(provider_type: str, api_key: str, base_url: Optional[str] = None):
        """Factory method to create appropriate provider instance"""
        if provider_type == ProviderType.OPENAI.value:
            return OpenAIProvider(api_key)
        elif provider_type == ProviderType.IONOS.value:
            return IONOSProvider(api_key, base_url)
        elif provider_type == ProviderType.GITHUB.value:
            return GitHubProvider(api_key, base_url)
        elif provider_type == ProviderType.OPENROUTER.value:
            return OpenRouterProvider(api_key, base_url)
        elif provider_type == ProviderType.ANTHROPIC.value:
            return AnthropicProvider(api_key)
        elif provider_type == ProviderType.AZURE.value:
            return AzureProvider(api_key, base_url)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

class OpenAIProvider(Provider):
    """OpenAI API provider"""

    def get_client(self):
        return openai.OpenAI(api_key=self.api_key)

    def get_completion(self, messages, tools, stream=True):
        client = self.get_client()
        return client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=stream,
        )

class IONOSProvider(Provider):
    """IONOS API provider"""

    def get_client(self):
        return openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_completion(self, messages, tools, stream=True):
        client = self.get_client()
        return client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=stream,
        )

class GitHubProvider(Provider):
    """GitHub AI Models provider"""

    def get_client(self):
        # For GitHub models, prioritize the environment variable token if available
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            api_key = github_token
        else:
            api_key = self.api_key

        # Use provided base_url if it exists, otherwise use the default GitHub endpoint
        base_url = self.base_url or "https://models.github.ai/inference"
        return openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def get_completion(self, messages, tools, stream=True):
        client = self.get_client()
        try:
            return client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                stream=stream,
                temperature=1.0,
                top_p=1.0,
                max_tokens=1024,
            )
        except Exception as e:
            print(f"Error calling GitHub AI: {e}")
            raise Exception(f"Error in GitHub AI call: {str(e)}")

class OpenRouterProvider(Provider):
    """OpenRouter API provider"""

    def get_client(self):
        base_url = self.base_url or "https://openrouter.ai/api/v1"
        return openai.OpenAI(api_key=self.api_key, base_url=base_url)

    def get_completion(self, messages, tools, stream=True):
        client = self.get_client()
        return client.chat.completions.create(
            model="openrouter/auto",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=stream,
        )

class AnthropicProvider(Provider):
    """Anthropic API provider"""

    def get_client(self):
        try:
            import anthropic
            return anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("The 'anthropic' package is required for using the Anthropic provider")

    def get_completion(self, messages, tools, stream=True):
        client = self.get_client()

        # Convert OpenAI format messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "user":
                anthropic_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                anthropic_messages.append({"role": "assistant", "content": msg["content"]})
            elif msg["role"] == "system":
                # System message is handled differently in Anthropic
                system_message = msg["content"]

        # Anthropic uses a different tools format, so we need to adapt
        tool_choice = None
        anthropic_tools = []

        for tool in tools:
            if tool["type"] == "function":
                anthropic_tools.append({
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "input_schema": tool["function"]["parameters"]
                })

        # Use Claude model
        response = client.messages.create(
            model="claude-3-opus-20240229",
            messages=anthropic_messages,
            system=system_message if "system_message" in locals() else None,
            tools=anthropic_tools if anthropic_tools else None,
            stream=stream
        )

        return response

class AzureProvider(Provider):
    """Azure OpenAI API provider"""

    def get_client(self):
        return openai.AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.base_url,
            api_version="2023-05-15"
        )

    def get_completion(self, messages, tools, stream=True):
        client = self.get_client()
        return client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=stream,
        )

def get_streaming_chat_response(messages, tools, current_user_config):
    """Get streaming chat response from the configured AI provider"""
    provider = Provider.create_provider(
        provider_type=current_user_config.provider_type,
        api_key=current_user_config.ai_key,
        base_url=current_user_config.base_url
    )

    try:
        return provider.get_completion(
            messages=messages,
            tools=tools,
            stream=True
        )
    except Exception as e:
        print(f"Error calling LLM: {e}")
        raise