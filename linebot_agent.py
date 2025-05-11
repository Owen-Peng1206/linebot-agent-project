#linebot_agent.py
import os
from openai import AsyncOpenAI
from typing import List, Dict
from linebot_tools import get_weather, translate_to_chinese, translate_to_english
from linebot_tools import translate_to_Japanese, translate_to_Korean, generate_image_and_get_url
from linebot_tools import web_search_tool, web_scrape_tool, UserInfo

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled

# OpenAI Agent configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or ""
LLM_API_KEY = os.getenv("LLM_API_KEY") or ""
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME") or ""

# Validate environment variables
if not LLM_BASE_URL or not LLM_API_KEY or not LLM_MODEL_NAME :
    raise ValueError(
        "Please set LLM_BASE_URL, LLM_API_KEY,LLM_MODEL_NAME via env var or code."
    )

# Initialize OpenAI client
client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
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
            model=LLM_MODEL_NAME, openai_client=client),
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
