import openai
from dotenv import load_dotenv

load_dotenv()

def get_streaming_chat_response(messages, tools, current_user_config):
    # Create the appropriate client based on the API key type
    is_openai = current_user_config.ai_key.startswith('sk-')
    is_github = current_user_config.ai_key.startswith('gh')
    is_ionos = not (is_openai or is_github)

    base_url = None
    model_name = None

    if is_openai:
        base_url = None
        model_name = "gpt-3.5-turbo"
    elif is_github:
        base_url = "https://models.github.ai/inference"
        model_name = "openai/gpt-4o-mini"

    elif is_ionos:
        if not current_user_config.ionos_base_url:
            raise ValueError("IONOS base URL is required for IONOS API keys")
        base_url = current_user_config.ionos_base_url
        model_name = "meta-llama/Llama-3.3-70B-Instruct"

    client = openai.OpenAI(
        api_key=current_user_config.ai_key,
        base_url=base_url,
        default_headers={"Authorization": f"Bearer {current_user_config.ai_key}"} if is_github else None
    )

    try:
        completion_params = {
            "model": model_name,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "stream": True,
        }

        if is_github:
            # Add GitHub-specific parameters
            completion_params.update({
                "stream_options": {"include_usage": True}
            })

        return client.chat.completions.create(**completion_params)
    except Exception as e:
        print(f"Error calling LLM: {e}")
        raise
