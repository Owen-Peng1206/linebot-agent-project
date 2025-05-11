# Linebot agent project (LINE Bot + FastAPI + OpenAI agent python SDK)

## Project Description

This project is an intelligent customer service system built on the LINE platform, integrating FastAPI, OpenAI models, and various tools. It uses Redis to store conversation history, supports natural language processing, weather information queries, image generation, and other multi-functional interactions.


## Demo

- Chat

![Chat.](https://github.com/Owen-Peng1206/linebot-agent-project/blob/main/image/4230b44fc4e4a2.gif?raw=true "Chat.")

- Get weather

![Get weather.](https://github.com/Owen-Peng1206/linebot-agent-project/blob/main/image/4ddc83c16c6601.gif?raw=true "Get weather.")

- Generate image

![Generate image.](https://github.com/Owen-Peng1206/linebot-agent-project/blob/main/image/4327111ec97a36.gif?raw=true "Generate image.")

## Features

- **Real-time conversation handling (supports clearing chat history)**  
- **Multilingual support** (Traditional Chinese / English / Japanese / Korean)  
- **Weather information lookup** (Integrated with OpenWeatherMap API)  
- **ComfyUI image generation service**  
- **Web search and content crawling features**  
- **Highly scalable tool architecture**

## Technologies Used

- __LINE Messaging API__ - The Line Messaging API establishes bidirectional communication between developer services and LINE users.
- __FastAPI__ - Handles LINE Bot Webhook  
- __OpenAI Agent framework__ - Intelligent conversation engine  
- __Redis__ - Conversation history storage and management  
- __ComfyUI__ - Image generation service  
- __Aiohttp__ - Asynchronous HTTP client  
- __Minio__ - Image data storage  
- __Docker__ - Containerized deployment solution

## Setup

1. Clone the repository to your local machine.
   ```
   git clone https://github.com/Owen-Peng1206/linebot-agent-project.git
   ```
2. Setting your environment variables:

   ```.env
    ChannelSecret="YOUR_LINE_CHANNEL_SECRET"
    ChannelAccessToken="YOUR_LINE_CHANNEL_ACCESS_TOKEN"
    LINE_CHAT_HISTORY_LENGTH="YOUR_LINE_CHAT_HISTORY_LENGTH" # e.g. 100    
    WEATHERMAP_API_KEY="YOUR_OPENWEATHERMAP_API_KEY"
    COMFYUI_WS_ENDPOINT="http://YOUR.COMFYUI.ADDRESS:PORT"
    COMFYUI_WORKFLOW_PATH="YOUR_COMFYUI_WORKFLOW_PATH" # e.g. data/COMFYUI_WORKFLOW.json    
    LLM_BASE_URL="YOUR_LLM_BASE_URL" # e.g. https://XXXLLM.YOUR_URL/openai/  
    LLM_API_KEY="YOUR_LLM_API_KEY" # e.g. sk-366df9446d3247e4b1107898ab25d5b5
    LLM_MODEL_NAME="YOUR_LLM_MODEL_NAME" # e.g. qwen3-30b-a3b
    REDIS_HOST_ADDRESS="YOUR.REDIS.HOST.ADDRESS" # e.g.192.168.50.100
    REDIS_HOST_PORT="YOUR.REDIS.HOST.PORT" # e.g. 6379
    GOOGLE_API_KEY="YOUR_GOOGLESEARCH_API_KEY" #your_google_api_key
    GOOGLE_CX="YOUR_GOOGLESEARCH_ENGINE_ID" #your_custom_search_engine_id
    SEARCH_ENGINE="YOUR_SEARCH_ENGINE"  # or "duckduckgo" "google"
    AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID" # e.g. 23TUJDWEJLKFRFGSBVSFGS
    AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY" # e.g. cbci00kwhYiuIpIX0kWLKLJDHUGDFBKSdobT
    AWS_S3_URL_API="YOUR_AWS_S3_URL_API" # e.g. https://XXXAWS.YOUR_URL:443
    AWS_S3_URL_WEBUI="YOUR_AWS_S3_URL_WEBUI" # e.g. https://XXXAWS.YOUR_URL
    AWS_S3_BUCKET ="YOUR_AWS_S3_BUCKET" # e.g. image    
   ```

3. Install necessory packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Start FastAPI service:

   ```bash
   uvicorn main:app --reload --host=0.0.0.0 --port=8001
   ```

5. Configure LINE Bot Webhook URL point to your Line Bot webhook address

## Usage

### Text Processing

- Supports natural conversation and multilingual switching  
- Automatically records conversation history (retains 41 entries)

### Useful tool

| Tool Name      | Function Description                     |
|----------------|------------------------------------------|
| get_weather    | Query city weather information         |
| generate_image | Generate images through ComfyUI        |
| web_search     | Web search (e.g., Google/DuckDuckGo)   |
| web_scrape     | Web content scraper                    |

## Deployment Options

### Local development

```bash
  uvicorn main:app --reload --host=0.0.0.0 --port=8001
```

### Docker depoly

Dockfile example:
```
    # Stage 1: Build (using a full development environment)
    FROM python:3.12 AS builder
    RUN pip install --user some-package

    # Stage 2: Final run image (keep only necessary files)
    FROM python:3.12-slim
    COPY --from=builder /root/.local /root/.local
    ENV PATH=/root/.local/bin:$PATH

    # Copy the project into the container
    # COPY ./app
    COPY *.py /app/
    COPY *.json /data/
    WORKDIR /app

    # Install necessary packages
    #RUN pip install --upgrade pip
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    EXPOSE 8001
    #CMD uvicorn main:app --host=0.0.0.0 --port=8080
    # Run with uvicorn
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

compose.yaml example:
```yaml
    services:
    linebot-agent-project:
        image: linebot-agent-project:latest
        container_name: linebot-agent-project
        ports:
        - 8001:8001
        volumes:
        - ./data:/data      
        environment:
            ChannelSecret : ${ChannelSecret}
            ChannelAccessToken : ${ChannelAccessToken}
            LINE_CHAT_HISTORY_LENGTH : ${LINE_CHAT_HISTORY_LENGTH}            
            WEATHERMAP_API_KEY : ${WEATHERMAP_API_KEY}
            COMFYUI_WS_ENDPOINT : ${COMFYUI_WS_ENDPOINT}
            COMFYUI_WORKFLOW_PATH : ${COMFYUI_WORKFLOW_PATH}              
            LLM_BASE_URL : ${LLM_BASE_URL}
            LLM_API_KEY : ${LLM_API_KEY}
            LLM_MODEL_NAME : ${LLM_MODEL_NAME}
            REDIS_HOST_ADDRESS : ${REDIS_HOST_ADDRESS}
            REDIS_HOST_PORT : ${REDIS_HOST_PORT}
            GOOGLE_API_KEY : ${GOOGLE_API_KEY} #your_google_searcg_api_key
            GOOGLE_CX : ${GOOGLE_CX} #your_custom_search_engine_id
            SEARCH_ENGINE : ${SEARCH_ENGINE}  # or "duckduckgo" "google"   
            AWS_ACCESS_KEY_ID : ${AWS_ACCESS_KEY_ID}
            AWS_SECRET_ACCESS_KEY : ${AWS_SECRET_ACCESS_KEY}
            AWS_S3_URL_API : ${AWS_S3_URL_API}
            AWS_S3_URL_WEBUI : ${AWS_S3_URL_WEBUI}
            AWS_S3_BUCKET  : ${AWS_S3_BUCKET}                
        restart: on-failure:5	      
        network_mode: host
```


docker-compose.yaml example:
```yaml
    services:
    linebot-agent-project:
        image: linebot-agent-project:latest
        container_name: linebot-agent-project
        build:
        context: .    
        ports:
        - 8001:8001
        volumes:
        - ./data:/data          
        environment:
            ChannelSecret : ${ChannelSecret}
            ChannelAccessToken : ${ChannelAccessToken}
            LINE_CHAT_HISTORY_LENGTH : ${LINE_CHAT_HISTORY_LENGTH}            
            WEATHERMAP_API_KEY : ${WEATHERMAP_API_KEY}
            COMFYUI_WS_ENDPOINT : ${COMFYUI_WS_ENDPOINT}
            COMFYUI_WORKFLOW_PATH : ${COMFYUI_WORKFLOW_PATH}                  
            LLM_BASE_URL : ${LLM_BASE_URL}
            LLM_API_KEY : ${LLM_API_KEY}
            LLM_MODEL_NAME : ${LLM_MODEL_NAME}
            REDIS_HOST_ADDRESS : ${REDIS_HOST_ADDRESS}
            REDIS_HOST_PORT : ${REDIS_HOST_PORT}
            GOOGLE_API_KEY : ${GOOGLE_API_KEY} #your_google_api_key
            GOOGLE_CX : ${GOOGLE_CX} #your_custom_search_engine_id
            SEARCH_ENGINE : ${SEARCH_ENGINE}  # or "duckduckgo" "google"   
            AWS_ACCESS_KEY_ID : ${AWS_ACCESS_KEY_ID}
            AWS_SECRET_ACCESS_KEY : ${AWS_SECRET_ACCESS_KEY}
            AWS_S3_URL_API : ${AWS_S3_URL_API}
            AWS_S3_URL_WEBUI : ${AWS_S3_URL_WEBUI}
            AWS_S3_BUCKET  : ${AWS_S3_BUCKET}             
      
        restart: on-failure:5
```


redis compose.yaml example:
```yaml
    version: '3.3'
    services:
    redis:
        image: redis:latest
        container_name: redis_contaier
        restart: on-failure:5	   
        ports:
        - '6379:6379'
        volumes:
        - ./data:/data
        - ./redis.conf:/usr/local/etc/redis/redis.conf
        - ./logs:/logs
        command: redis-server /usr/local/etc/redis/redis.conf
```

minio compose.yaml example:
```yaml
version: '3'

services:
  minio:
    image: minio/minio:latest
    ports:
      - 9000:9000
      - 9001:9001
    networks:
      - minionetwork
    volumes:
      - './data:/data'
      - './config:/root/.minio'
    environment:
      - MINIO_ROOT_USER=admin
      - MINIO_ROOT_PASSWORD=YOUR_PASSWORD
    command: server /data --address=":9000" --console-address=":9001"
networks:
  minionetwork:
    driver: bridge
```

1. Build image:

   ```bash
   docker build -t linebot-agent-project:latest .
   ```

2. Run container:

   ```bash
   docker compose run --remove-orphans linebot-agent-project
   ```
3. tag your image

   ```bash
   docker tag linebot-agent-project:latest hub.YOUR_REGISTRY/linebot-agent-project:latest
   ```   

4. Push your image

   ```bash
   docker push hub.YOUR_REGISTRY/linebot-agent-project:latest
   ```  

### Note

Before using the generate image function, you need to make sure that ComfyUI and minio have been built, and that you can generate images for text in ComfyUI through the correct WORKFLOW.json