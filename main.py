import os
import json
import aiohttp
import redis
import tiktoken
from fastapi import Request, FastAPI, HTTPException
from linebot_agent import generate_text_with_agent
from linebot.models import (
    MessageEvent, TextSendMessage, ImageSendMessage
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot import (
    AsyncLineBotApi, WebhookParser
)
from linebot_tools import MINIO_URL_API
import re  # New import for URL pattern matching

# LINE Bot configuration
LINE_CHANNEL_SECRET = os.getenv('ChannelSecret', None)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('ChannelAccessToken', None)
LINE_CHAT_HISTORY_LENGTH = os.getenv("LINE_CHAT_HISTORY_LENGTH") or "41"

# REDIS SERVER configuration
REDIS_HOST_ADDRESS = os.getenv("REDIS_HOST_ADDRESS") or ""
REDIS_HOST_PORT = os.getenv("REDIS_HOST_PORT") or ""
REDIS_HOST_PASS = os.getenv("REDIS_HOST_PASS") or ""

# Validate environment variables

if not LINE_CHANNEL_SECRET :
    raise ValueError(
        "Please set LINE_CHANNEL_SECRET via env var or code."
    )
if not LINE_CHANNEL_ACCESS_TOKEN :
    raise ValueError(
        "Please set LINE_CHANNEL_ACCESS_TOKEN via env var or code."
    )

if not REDIS_HOST_ADDRESS or not REDIS_HOST_PORT :
    raise ValueError(
        "Please set REDIS_HOST_ADDRESS, REDIS_HOST_PORT via env var or code."
    )

# Initialize the Redis connection pool
redis_pool = redis.ConnectionPool(
    host=os.getenv("REDIS_HOST", REDIS_HOST_ADDRESS),
    port=int(os.getenv("REDIS_PORT", REDIS_HOST_PORT)),
    db=int(os.getenv("REDIS_DB", "0")),
    password=os.getenv("REDIS_PASSWORD", REDIS_HOST_PASS),
)
redis_client = redis.Redis(connection_pool=redis_pool)

# Initialize the FastAPI app for LINEBot
app = FastAPI()
session = aiohttp.ClientSession()
async_http_client = AiohttpAsyncHttpClient(session)
line_bot_api = AsyncLineBotApi(LINE_CHANNEL_ACCESS_TOKEN, async_http_client)
parser = WebhookParser(LINE_CHANNEL_SECRET)


@app.post("/webhook")
async def handle_callback(request: Request):
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = await request.body()
    body = body.decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if not isinstance(event, MessageEvent):
            continue

        user_id = event.source.user_id
        # print(f"[debug] Get user_ide: {user_id}")
        msg = event.message.text.strip()
        # Processing "clear" commands
        if msg == "清除" or msg == "clear" or msg == "reset" or msg == "Reset" or msg == "RESET" or msg == "CLEAR" or msg == "Clear" or msg == "/reset":
            #print(f"[debug] User requested to clear chat history") 
            redis_client.delete(get_conversation_key(user_id))
            await line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="Clear conversation history!")
            )
            continue

        # Get the conversation history (initialize if it does not exist)
        history_str = redis_client.get(get_conversation_key(user_id))
        #print(f"[debug] Get chat history from redis database: {history_str}")
        if not history_str:
            initial_history = [{"role": "system", "content": "You are a helpful assistant that responds in Traditional Chinese (zh-TW) or english. Provide informative and helpful responses. if you descide to use th eget_weather () function, please translate the city name to english. Please refer to the conversation history to provide a coherent and natural response."}]
            redis_client.setex(get_conversation_key(user_id), 86400, json.dumps(initial_history))  # Automatically delete after 1 day
            #print(f"[debug] No chat history found, initializing with system prompt")
            history = initial_history
        else:
            history = json.loads(history_str)
            #print(f"[debug-true] Get chat history from redis database: {history_str}")

        # Limit to max XX messages if needed
        if len(history) > int(LINE_CHAT_HISTORY_LENGTH):
            history = history[-int(LINE_CHAT_HISTORY_LENGTH):]

        # Initialize tokenizer
        tokenizer = tiktoken.get_encoding("cl100k_base")
        MAX_TOKENS = 4096  # Adjust this value as needed

        # Check user message token count
        user_msg_tokens = len(tokenizer.encode(msg))
        if user_msg_tokens > MAX_TOKENS:
            await line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"提示過長 ({user_msg_tokens} tokens > {MAX_TOKENS} tokens). 請簡化提示。")
            )
            return "OK"


        # Add user message to history
        history.append({"role": "user", "content": msg})
        # history.append({"role": "user", "content": f'reply_token='+event.reply_token})
        print(f"[debug] main.py reply_token: {event.reply_token}")
        if len(history) > int(LINE_CHAT_HISTORY_LENGTH):
            history = history[-int(LINE_CHAT_HISTORY_LENGTH):]

        # Add user messages to history
        # Generate response
        response = await generate_text_with_agent(history, event.reply_token)

        # Check response token count
        response_tokens = len(tokenizer.encode(response))
        if response_tokens > MAX_TOKENS:
            # Truncate to MAX_TOKENS tokens
            truncated_response = tokenizer.decode(
                tokenizer.encode(response)[:MAX_TOKENS]
            )
            response = truncated_response

        reply_msg = TextSendMessage(text=response)

        # Update history (set TTL)
        history.append({"role": "assistant", "content": response})
        if len(history) > int(LINE_CHAT_HISTORY_LENGTH):
            history = history[-int(LINE_CHAT_HISTORY_LENGTH):]

        redis_client.setex(get_conversation_key(user_id), 86400, json.dumps(history))  # 1天後自動刪除

        # Check for MinIO URLs in the response and send them
        pattern_str = fr'{MINIO_URL_API}/.+?\.png'
        pattern = re.compile(pattern_str)
        matches = re.findall(pattern, response)
        # print(f"matches image_url = '{matches}' ")

        if matches:
            await send_minio_image(event.reply_token, matches[0])
            return 'OK'  # Early exit after sending the image
        else:
            await line_bot_api.reply_message(event.reply_token, reply_msg)
            
    return 'OK'


# Using Redis to store conversation history
def get_conversation_key(user_id):
    return f"conversation:{user_id}"

async def send_minio_image(reply_token: str, image_url):
    """
    Send an image to the user using the provided reply token and image URL.
    
    Args:
        reply_token: Token from Line event to reply to
        image_url: URL of the image to send
    """
    message = ImageSendMessage(
        original_content_url=image_url,
        preview_image_url=image_url
    )
    
    # Use aiohttp for asynchronous HTTP requests
    async with aiohttp.ClientSession() as session:
        await line_bot_api.reply_message(
            reply_token=reply_token,
            messages=message
        )