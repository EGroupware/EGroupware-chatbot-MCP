import os
import openai
from dotenv import load_dotenv

load_dotenv()

def get_streaming_chat_response(messages, tools, current_user_config):
    # Create the appropriate client based on the API key type
    is_openai = current_user_config.ai_key.startswith('sk-')

    client = openai.OpenAI(
        api_key=current_user_config.ai_key,
        base_url=None if is_openai else current_user_config.ionos_base_url
    )

    try:
        return client.chat.completions.create(
            model="gpt-3.5-turbo" if is_openai else "meta-llama/Llama-3.3-70B-Instruct",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=True,
        )
    except Exception as e:
        print(f"Error calling LLM: {e}")
        raise