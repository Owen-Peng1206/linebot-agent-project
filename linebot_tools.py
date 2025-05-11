#linebot_tools.py
import os
import json
import requests
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from agents import function_tool, RunContextWrapper
import random
import uuid
import boto3
from io import BytesIO
import logging
from dataclasses import dataclass

@dataclass
class UserInfo:
    name: str
    uid: str

# Openweathermap API key
OPENWEATHERMAP_API_KEY = os.getenv("WEATHERMAP_API_KEY") or ""

# Configuration Search tool from environment variables
search_engine = os.getenv("SEARCH_ENGINE", "duckduckgo").lower()
google_api_key = os.getenv("GOOGLE_API_KEY")
google_cx = os.getenv("GOOGLE_CX")

# comfyUI configuration
client_id = str(uuid.uuid4())
COMFYUI_API_URL =  os.getenv("COMFYUI_WS_ENDPOINT")  # replace to your ComfyUI API URL
COMFYUI_CLIENT_ID = client_id  
MINIO_URL_API = os.getenv("AWS_S3_URL_API") 
MINIO_URL_WEBUI = os.getenv("AWS_S3_URL_WEBUI")
MINIO_BUCKET = os.getenv("AWS_S3_BUCKET") 
MINIO_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")  
MINIO_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
MINIO_region_name = "us-east-1"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not OPENWEATHERMAP_API_KEY:
    raise ValueError(
        "Please set WEATHERMAP_API_KEY via env var or code."
    )

@function_tool
def web_scrape_tool(url: str):
    """Scrape text content from a URL."""
    print(f"[debug] Scrape web for: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return {
            "status": 200,
            "content": soup.get_text(strip=True)[:2000]  # Return first 2000 characters
        }
    except Exception as e:
        return {"status": 500, "error": str(e)}

@function_tool
def web_search_tool(prompt: str):
    """Perform a web search using configurable API (Google or DuckDuckGo)"""
    print(f"[debug] Searching web for: {prompt}")
       
    try:
        if search_engine == "google":
            # Google Search API implementation
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': google_api_key,
                'cx': google_cx,
                'q': prompt,
                'num': 10  # Return 3 results
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            results = []
            if 'items' in data:
                for result in data['items'][:10]:  # Get top 10 results
                    results.append(f"{result['title']} - {result['link']}")
                    
            return "\n".join(results)
            
        else:
            # DuckDuckGo API implementation
            url = "https://api.duckduckgo.com/search"
            params = {
                'q': prompt,
                'format': 'json'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            results = []
            if 'Web' in data:
                for result in data['Web'][:10]:  # Get top 10 results
                    results.append(f"{result['Title']} - {result['Url']}")
                    
            return "\n".join(results)
            
    except Exception as e:
        print(f"[error] Web search failed: {str(e)}")
        return f"Can not finish search: {str(e)}"

  
def upload_image_to_s3(image_url, bucket_name, s3_key, s3_endpoint=None):
    """Upload image from URL to AWS S3 with customizable endpoint"""
    try:
        # Download image from ComfyUI
        response = requests.get(image_url)
        response.raise_for_status()

        # Configure S3 client with optional custom endpoint using correct Config class
        s3_config = boto3.session.Config(signature_version='s3v4')
        s3_client = boto3.client(
            's3',
            endpoint_url=s3_endpoint,  # Replace with your S3 server URL
            use_ssl=True,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name=MINIO_region_name,
            config=s3_config
        )

        # Check if Bucket exists (boto3 does not have a direct bucket_exists method, exceptions need to be caught)
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except s3_client.exceptions.NoSuchBucket:
            s3_client.create_bucket(Bucket=bucket_name)

        # Upload to S3
        s3_client.upload_fileobj(BytesIO(response.content), bucket_name, s3_key)

        # Set Bucket Policy to public
        policy_json = json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "*",
                    "Resource": f"arn:aws:s3:::image/*"
                }
            ]
        })     

        s3_client.put_bucket_policy(Bucket=bucket_name, Policy=policy_json)
        # print(f"Bucket '{bucket_name}' policy set to allow public read access")

        # Get file URL
        public_url_https = f"{MINIO_URL_API}/{bucket_name}/{s3_key}"
        # print(f"Public URL for '{s3_key}': {public_url_https}")

        return public_url_https

    except requests.exceptions.RequestException as e:
        print(f"Error downloading file from URL: {str(e)}")        
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

# From server file load COMFYUI_WORKFLOW.json
def load_comfy_workflow(workflow_path="COMFYUI_WORKFLOW.json"):
    """Read COMFYUI_WORKFLOW.json from the specified path, supporting absolute/relative paths"""
    try:
        # Check if the file exists
        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"Workflow file not found: {workflow_path}")
        
        # Use absolute paths to avoid path problems
        abs_path = os.path.abspath(workflow_path)
        logger.info(f"Reading workflow archive: {abs_path}")
        
        with open(abs_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
            
        # Verify infrastructure
        if not isinstance(workflow, dict):
            raise ValueError("The JSON file format does not match the expected format (object is required)")
            
        return workflow
        
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON parsing failed: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to load workflow: {e}") from e
    

def generate_image_with_comfyui(prompt):
    """Generate image using ComfyUI API and return the prompt ID."""
    # Initial comfyUI WORKFLOW json
    try:
        # Load the workflow from the specified path (example: COMFYUI_WORKFLOW_PATH=custom_workflow.json)
        workflow_path = os.getenv("COMFYUI_WORKFLOW_PATH", "COMFYUI_WORKFLOW.json")
        COMFYUI_WORKFLOW = load_comfy_workflow(workflow_path)
        
    except Exception as e:
        logger.error(f"Failed to initialize workflow: {str(e)}")
        # Handle the error as needed
        COMFYUI_WORKFLOW = {}  # 或 raise SystemExit()

    workflow = COMFYUI_WORKFLOW.copy()
    #set the text prompt for our positive CLIPTextEncode
    workflow["6"]["inputs"]["text"] = prompt

    #set the seed for our KSampler node
    workflow["10"]["inputs"]["noise_seed"] = random.randint(1, 49999)
    workflow["11"]["inputs"]["noise_seed"] = random.randint(50000, 99999)

    payload = {"prompt": workflow}
    if COMFYUI_CLIENT_ID:
        payload["client_id"] = COMFYUI_CLIENT_ID
    try:
        response = requests.post(f"{COMFYUI_API_URL}/prompt", json=payload)
        response.raise_for_status()
        data = response.json()
        prompt_id = data.get("prompt_id")
        return prompt_id
    except requests.exceptions.RequestException as e:
        return f"ComfyUI API request failed: {e}"

def get_image_url_from_comfyui(prompt_id):
    """Poll the ComfyUI API to get the generated image URL."""
    if not prompt_id:
        return None
    history_url = f"{COMFYUI_API_URL}/history/{prompt_id}"
    for _ in range(30):
        try:
            response = requests.get(history_url)
            response.raise_for_status()
            data = response.json()
            if prompt_id in data:
                outputs = data[prompt_id]["outputs"]
                for node_output in outputs.values():
                    for image in node_output["images"]:
                        filename = image["filename"]
                        subfolder = image["subfolder"]
                        image_url = f"{COMFYUI_API_URL}/view?filename={filename}&subfolder={subfolder}&type=output"
                        #return image_url
                        s3_bucket = MINIO_BUCKET
                        s3_key = f"{uuid.uuid4()}.png"  # Use unique key for each upload
                        custom_s3_endpoint = MINIO_URL_API
                        
                        return upload_image_to_s3(
                            image_url, 
                            s3_bucket, 
                            s3_key,
                            s3_endpoint=custom_s3_endpoint
                        )

                break
        except requests.exceptions.RequestException as e:
            return f"ComfyUI History API request failed: {e}"
        import time
        time.sleep(2)
    return "Image generation timed out or failed. "


@function_tool
async def generate_image_and_get_url(wrapper: RunContextWrapper[UserInfo], prompt: str ) -> str: 
    """    Generate an image based on the provided prompt and return its URL.
        Args:
            prompt: This refers to a message or instruction displayed to the user 
            reply_token: It is a unique identifier used by Line Bot to correctly respond to user messages.

    """
    print(f"[debug] reply_token: {wrapper.context.uid}")

    image_prompt = "if you decide to use the generate_image_and_get_url(), translate the prompt to englist first. please add prompt masterpiece, best quality, ultra-detailed, 8K, RAW photo, intricate details, stunning visuals,upper-body," \
            "cinematic lighting, soft focus,(white background:1.05)realistic,photorealistic,masterpiece,best quality,newest,highres,absurdres,photo," \
            "cosplay photo,photo (medium), dslr, real life, real life insert, real world location, photo background." 
    prompt += image_prompt
    prompt_id = generate_image_with_comfyui(prompt)

    if isinstance(prompt_id, str) and prompt_id.startswith("ComfyUI API request error"):
        return prompt_id
    image_url = get_image_url_from_comfyui(prompt_id)
    return image_url


@function_tool
async def get_weather(city: str):
    """Get weather information for a city using OpenWeatherMap API"""
    print(f"[debug] getting weather for {city}")

    # Base URLs for current and forecast data
    base_url_current = "https://api.openweathermap.org/data/2.5/weather"
    base_url_forecast = "https://api.openweathermap.org/data/2.5/forecast"

    async with aiohttp.ClientSession() as session:
        try:
            # Prepare parameters
            params = {
                'q': city,
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',  # Metric units (Celsius)
            }
            
            # Fetch current weather
            async with session.get(base_url_current, params=params) as response:
                if response.status == 200:
                    current_weather_data = await response.json()
                    current_weather = (
                        f"Current weather in {city}: "
                        f"{current_weather_data['weather'][0]['description']}, "
                        f"Temperature: {current_weather_data['main']['temp']}°C"
                    )
                else:
                    return f"Error fetching current weather: {response.status}"

            # Fetch 5-day forecast
            async with session.get(base_url_forecast, params=params) as response:
                if response.status == 200:
                    forecast_data = await response.json()
                    
                    # Process today's time-specific weather
                    today_weather = []
                    today_date = datetime.now().date()
                    
                    for item in forecast_data['list']:
                        dt = datetime.strptime(item['dt_txt'], "%Y-%m-%d %H:%M:%S")
                        
                        # Check if this is today's weather
                        if dt.date() == today_date:
                            time_of_day = "Morning" if 6 <= dt.hour < 12 else \
                                         "Afternoon" if 12 <= dt.hour < 18 else \
                                         "Evening"
                            
                            today_weather.append({
                                'time': f"{dt.strftime('%H:%M')}",
                                'description': item['weather'][0]['description'],
                                'temperature': item['main']['temp']
                            })
                    
                    # Format today's time-specific weather
                    today_summary = "Today's Weather by Time:\n" + "\n".join(
                        f"{w['time']}: {w['description']}, {w['temperature']}°C"
                        for w in today_weather
                    )
                    

                    # Process 5-day forecast for high/low temps and weather
                    daily_temps = {}
                    for item in forecast_data['list']:
                        dt = datetime.strptime(item['dt_txt'], "%Y-%m-%d %H:%M:%S")
                        date_str = dt.strftime("%Y-%m-%d")
                        temp = item['main']['temp']
                        weather_desc = item['weather'][0]['description']

                        if date_str not in daily_temps:
                            daily_temps[date_str] = {
                                'temps': [temp],
                                'weather': weather_desc  # Store the first weather description for the day
                            }
                        else:
                            daily_temps[date_str]['temps'].append(temp)
                    
                    # Sort dates and take first 5
                    sorted_dates = sorted(daily_temps.keys())
                    forecast_days = []
                    for date in sorted_dates[:5]:
                        data = daily_temps[date]
                        max_temp = max(data['temps'])
                        min_temp = min(data['temps'])
                        forecast_days.append({
                            'date': date,
                            'high': max_temp,
                            'low': min_temp,
                            'weather': data['weather']
                        })
                    
                    # Format the forecast summary with high/low info and weather
                    forecast_summary = "5-day forecast:\n" + "\n".join(
                        f"{day['date']}: High {day['high']}°C, Low {day['low']}°C, Weather: {day['weather']}"
                        for day in forecast_days
                    )
                else:
                    return f"Error fetching 5-day forecast: {response.status}"
            
            # Combine results with new time-specific weather
            result = current_weather + "\n\n" + today_summary + "\n\n" + forecast_summary
            print(f"[debug] got weather info for {city}")
            return result
        
        except Exception as e:
            return f"Error retrieving weather data: {str(e)}"
    
@function_tool
def translate_to_english(text: str):
    """Translate text to English"""
    print(f"[debug] translating to English: {text}")
    # This is a placeholder for actual translation logic.
    # You might use an external service or library here.
    return f"Translating to English: {text}"

@function_tool
def translate_to_chinese(text: str):
    """Translate text to Traditional Chinese"""
    print(f"[debug] translating: {text}")
    # This is a placeholder for actual translation logic.
    # You might use an external service or library here.    
    return f"Translating to Chinese: {text}"

@function_tool
def translate_to_Japanese(text: str):
    """Translate text to Japanese"""
    print(f"[debug] translating to Japanese: {text}")
    # This is a placeholder for actual translation logic.
    # You might use an external service or library here.    
    return f"Translating to Japanese: {text}"

@function_tool
def translate_to_Korean(text: str):
    """Translate text to Korean"""
    print(f"[debug] translating to Korean: {text}")
    # This is a placeholder for actual translation logic.
    # You might use an external service or library here.    
    return f"Translating to Korean: {text}"    