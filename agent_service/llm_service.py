import os
import openai
from dotenv import load_dotenv

load_dotenv()

# client = openai.OpenAI(
#     api_key=os.getenv("IONOS_API_KEY"),
#     base_url=os.getenv("IONOS_API_BASE_URL"),
# )
# MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct"
#
# def get_streaming_chat_response(messages, tools):
#     try:
#         return client.chat.completions.create(
#             model=MODEL_NAME,
#             messages=messages,
#             tools=tools,
#             tool_choice="auto",
#             stream=True,
#         )
#     except Exception as e:
#         print(f"Error calling LLM: {e}")
#         raise
#



# ---  Using Openai API ---

client = openai.OpenAI()
MODEL_NAME = "gpt-4o"


def get_streaming_chat_response(messages, tools):
    """
    Gets a streaming response from the OpenAI LLM.
    This function's logic does not need to change at all.
    """
    try:
        # The call remains identical, just the client configuration and model name have changed.
        return client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=True,
        )
    except openai.APIConnectionError as e:
        print(f"OpenAI Server connection error: {e.__cause__}")
        raise
    except openai.RateLimitError as e:
        print(f"OpenAI Rate limit exceeded: {e.status_code} {e.response}")
        raise
    except openai.APIStatusError as e:
        print(f"OpenAI API Status Error: {e.status_code} {e.response}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise