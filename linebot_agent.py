#linebot_agent.py
import os
from openai import AsyncOpenAI
from typing import List, Dict
from linebot_tools import get_weather, translate_to_chinese, translate_to_english
from linebot_tools import translate_to_Japanese, translate_to_Korean, generate_image_and_get_url
from linebot_tools import web_search_tool, web_scrape_tool, UserInfo

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled

# OpenAI Agent configuration
OPENAI_BASE_URL = os.getenv("OPENAI_COMPATIBLE_API_BASE_URL") or ""
OPENAI_API_KEY = os.getenv("OPENAI_COMPATIBLE_API_KEY") or ""
OPENAI_MODEL_NAME = os.getenv("OPENAI_COMPATIBLE_API_MODEL_NAME") or ""

# Validate environment variables
if not OPENAI_BASE_URL or not OPENAI_API_KEY or not OPENAI_MODEL_NAME :
    raise ValueError(
        "Please set OPENAI_BASE_URL, OPENAI_API_KEY,OPENAI_MODEL_NAME via env var or code."
    )

# Initialize OpenAI client
client = AsyncOpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)
set_tracing_disabled(disabled=True)



async def generate_text_with_agent(history: List[Dict], reply_token: str):
    """
    Generate a text completion using OpenAI Agent with full conversation context.
    """
    User_Info = UserInfo(name = "demo", uid=reply_token)
    # Create agent with appropriate instructions
    agent = Agent[UserInfo](
        name="Assistant",
        instructions="You are a helpful assistant that responds in Traditional Chinese (zh-TW) or english. Provide informative and helpful responses. "\
            "if you decide to use the get_weather() function, please translate the city name to english and Enhance the formatting of the weather forecast and add weather icons." \
            "Please refer to the conversation history to provide a coherent and natural response.",
        model=OpenAIChatCompletionsModel(
            model=OPENAI_MODEL_NAME, openai_client=client),
        tools=[get_weather, 
               translate_to_chinese, 
               translate_to_english, 
               translate_to_Japanese, 
               translate_to_Korean, 
               generate_image_and_get_url,
               web_search_tool,
               web_scrape_tool
               ],
    )

    try:
        result = await Runner.run(
                    agent,
                    history, 
                    context=User_Info,
                    )
        return result.final_output
    except Exception as e:
        print(f"Error with LLM Agent: {e}")
        return f"Sorry, process your request error!  {str(e)}"
