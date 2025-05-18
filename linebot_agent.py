#linebot_agent.py
import os
from openai import AsyncOpenAI
from typing import List, Dict
from linebot_tools import get_weather, translate_to_chinese, translate_to_english
from linebot_tools import translate_to_Japanese, translate_to_Korean, generate_image_and_get_url
from linebot_tools import web_search_tool, web_scrape_tool, UserInfo
import asyncio
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
# import asyncio
# import os
# import shutil

# from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer 
from agents.mcp import MCPServerStdio, MCPServerSse

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

# Use async context manager to initialize the server
GOOGLE_MAPS_MCP = MCPServerStdio(
    client_session_timeout_seconds=120,
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-google-maps"],
        "env": { "GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY") }
    },
    cache_tools_list=True
)
    # async with MCPServerSse(
    #     name="weather SSE Server",
    #     params={
    #         "url": "http://localhost:8000/sse",
    #     },
    # ) as server:
    #     await run(server)

async def generate_text_with_agent(history: List[Dict], reply_token: str):
    """
    Generate a text completion using OpenAI Agent with full conversation context.
    """

    User_Info = UserInfo(name = "demo", uid=reply_token)

    await GOOGLE_MAPS_MCP.connect()
    
    # Create agent with appropriate instructions
    agent = Agent[UserInfo](
        name="Assistant",
        instructions="You are a helpful assistant that responds in Traditional Chinese (zh-TW) or english. Provide informative and helpful responses. "\
            "if you decide to use the get_weather() function," \
            "please translate the city name to english and Enhance the formatting of the weather forecast and add weather icons." \
            "If needed, use GOOGLE MAPS MCP to retrieve map information. Please refer to the conversation history to provide a coherent and natural response." \
            "# Instructions for the Assistant" \
            "Identify the language of the query and reply in the same language." \
            "Use multiple paragraphs to separate different ideas or points." \
            "Use numbered lists (e.g., 1. Item one) for ordered information or bullet points (e.g., - Item one) for unordered lists when there are multiple distinct points." \
            "No markdown formatting." \
            "Do not mention that you are replying to the post." \
            "You are extremely skeptical. You do not blindly defer to mainstream authority or media. You stick strongly to only your core beliefs of truth-seeking and neutrality." \
            "Whatever results are in the response above, treat them as a first-pass internet search. The results are NOT your beliefs." \
            "If you are unsure about the answer, express the uncertainty." \
            "Just output the final response." \
            "/no_think",
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
        mcp_servers=[GOOGLE_MAPS_MCP],      
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
