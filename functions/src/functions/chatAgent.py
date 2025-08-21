import boto3
import json
import os
import logging
from botocore.exceptions import ClientError
from .supported_model_list import MODELS_WITH_STREAMING_SUPPORT

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Defaults
DEFAULT_MODEL_ID = os.environ.get("DEFAULT_MODEL_ID", "anthropic.claude-instant-v1")
AWS_REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
DEFAULT_MAX_TOKENS = 256
DEFAULT_TEMPERATURE = 0

# global variables - avoid creating a new client for every request
bedrock_client = None
apigw_client = None


def construct_request_body(modelId, parameters, prompt):
    # Handle inference profile ARNs
    if modelId.startswith("arn:aws:bedrock"):
        provider = modelId.split("/")[-1].split(".")[1] if "/" in modelId else "unknown"
    else:
        provider = modelId.split(".")[0]
    request_body = None
    max_tokens = parameters.get('maxTokens', DEFAULT_MAX_TOKENS)
    temperature = parameters.get('temperature', DEFAULT_TEMPERATURE)

    # construct request body depending on model provider
    if provider == "anthropic":
        # Check if it's a newer Claude model that uses messages format
        if any(x in modelId for x in ["claude-3", "claude-4", "claude-3.5", "claude-3.7"]):
            request_body = {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "anthropic_version": "bedrock-2023-05-31"
            }
        else:
            # Legacy format for older Claude models
            request_body = {
                "prompt": prompt,
                "max_tokens_to_sample": max_tokens,
                "temperature": temperature
            }
    elif provider == "amazon":
        # Handle Nova models vs Titan models
        if "nova" in modelId:
            request_body = {
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature
                }
            }
        else:
            # Titan models
            textGenerationConfig = {
                "maxTokenCount": max_tokens,
                "temperature": temperature
            }
            request_body = {
                "inputText": prompt,
                "textGenerationConfig": textGenerationConfig
            }
    elif provider == "cohere":
        request_body = {
            "message": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
    elif provider == "meta":
        request_body = {
            "prompt": prompt,
            "max_gen_len": max_tokens,
            "temperature": temperature
        }
    elif provider == "ai21":
        request_body = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
    elif provider == "deepseek":
        request_body = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

    return request_body


def get_generated_text(modelId, response):
    # Handle inference profile ARNs
    if modelId.startswith("arn:aws:bedrock"):
        provider = modelId.split("/")[-1].split(".")[1] if "/" in modelId else "unknown"
    else:
        provider = modelId.split(".")[0]
    generated_text = None
    
    if provider == "anthropic":
        # Check if it's a newer Claude model that uses delta format
        if any(x in modelId for x in ["claude-3", "claude-4", "claude-3.5", "claude-3.7"]):
            # New format: delta in content_block_delta events
            if response.get("type") == "content_block_delta":
                delta = response.get("delta", {})
                generated_text = delta.get("text", "")
            elif response.get("type") == "message_delta":
                # Handle message delta events
                generated_text = ""
        else:
            # Legacy format
            generated_text = response.get("completion", "")
    elif provider == "amazon":
        if "nova" in modelId:
            # Nova models use delta format
            if response.get("contentBlockDelta"):
                generated_text = response.get("contentBlockDelta", {}).get("delta", {}).get("text", "")
            elif response.get("outputText"):
                generated_text = response.get("outputText", "")
        else:
            # Titan models
            generated_text = response.get("outputText", "")
    elif provider == "cohere":
        # Handle both old and new Cohere response formats
        if response.get("text"):
            generated_text = response.get("text", "")
        elif response.get("generations"):
            generated_text = response.get("generations", [{}])[0].get("text", "")
    elif provider == "meta":
        generated_text = response.get("generation", "")
    elif provider == "ai21":
        # AI21 models typically use choices format
        if response.get("choices"):
            generated_text = response.get("choices", [{}])[0].get("delta", {}).get("content", "")
        elif response.get("completion"):
            generated_text = response.get("completion", "")
    elif provider == "deepseek":
        # DeepSeek uses choices format similar to OpenAI
        if response.get("choices"):
            generated_text = response.get("choices", [{}])[0].get("delta", {}).get("content", "")
    
    return generated_text if generated_text is not None else ""


def try_send_to_websocket(apig_management_client, connection_id, message):
    """
    Resilient WebSocket sender - continues processing even if connection fails
    """
    try:
        apig_management_client.post_to_connection(
            Data=message, ConnectionId=connection_id
        )
        return True
    except ClientError as e:
        logger.warning(f"Failed to send to WebSocket {connection_id}: {e}")
        return False
    except Exception as e:
        logger.warning(f"WebSocket connection {connection_id} error: {e}")
        return False


def process_chat_message(connection_id, apig_management_client, parameters, prompt):
    """
    Resilient chat processing that continues even if WebSocket connection drops
    """
    global bedrock_client

    # Check if model supports streaming response
    modelId = parameters.pop("modelId", DEFAULT_MODEL_ID)
    if modelId not in MODELS_WITH_STREAMING_SUPPORT:
        error_msg = f"Model does not support streaming: {modelId}"
        logger.error(error_msg)
        try_send_to_websocket(apig_management_client, connection_id, error_msg)
        return 400, None

    body = construct_request_body(modelId, parameters, prompt)
    if body == None:
        error_msg = f"Unsupported provider: {modelId.split('.')[0]}"
        logger.error(error_msg)
        try_send_to_websocket(apig_management_client, connection_id, error_msg)
        return 400, None

    logger.info(f"Processing chat with ModelId: {modelId}")

    if (bedrock_client is None):
        bedrock_client = boto3.client(service_name='bedrock-runtime', region_name=AWS_REGION)

    try:
        response = bedrock_client.invoke_model_with_response_stream(
            body=json.dumps(body), 
            modelId=modelId, 
            accept='application/json', 
            contentType='application/json'
        )
        stream = response.get('body')
        
        complete_response = ""
        connection_alive = True
        
        if stream:
            for event in stream:
                chunk = event.get('chunk')
                if chunk:
                    try:
                        chunk_obj = json.loads(chunk.get('bytes').decode())
                        
                        # extract generated text based on model provider
                        generated_text = get_generated_text(modelId, chunk_obj)
                        
                        if generated_text:
                            complete_response += generated_text
                            
                            # Try to stream, but don't fail if connection is gone
                            if connection_alive:
                                if not try_send_to_websocket(apig_management_client, connection_id, generated_text):
                                    logger.info(f"WebSocket {connection_id} disconnected, continuing processing...")
                                    connection_alive = False
                                    
                    except Exception as e:
                        logger.error(f"Error processing chunk: {str(e)}")
                        # Continue processing even if individual chunks fail

            # Send end message if connection is still alive
            if connection_alive:
                try_send_to_websocket(apig_management_client, connection_id, "<End of LLM response>")
            
            logger.info(f"Chat processing completed. Response length: {len(complete_response)}")
            return 200, complete_response
    
    except Exception as e:
        error_msg = f"Error processing chat: {str(e)}"
        logger.error(error_msg)
        try_send_to_websocket(apig_management_client, connection_id, error_msg)
        return 500, None


def handler(event, context):
    global apigw_client

    logger.info(f"Chat Agent Event: {json.dumps(event)}")

    # Get connection info from WebSocket event
    connection_id = event.get("requestContext", {}).get("connectionId")
    route_key = event.get("requestContext", {}).get("routeKey")
    
    if not connection_id or not route_key:
        logger.error("Missing connection_id or route_key")
        return {"statusCode": 400}

    # Extract message info
    try:
        body = json.loads(event.get("body", "{}"))
        prompt = body.get("prompt", "")
        parameters = body.get("parameters", {})
        
        if not prompt:
            logger.error("Missing prompt in message body")
            return {"statusCode": 400}
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message body: {e}")
        return {"statusCode": 400}

    # Set up API Gateway management client
    domain = event.get("requestContext", {}).get("domainName")
    stage = event.get("requestContext", {}).get("stage")
    
    if not domain or not stage:
        logger.error("Missing domain or stage from request context")
        return {"statusCode": 400}

    if apigw_client is None:
        apigw_client = boto3.client("apigatewaymanagementapi", endpoint_url=f"https://{domain}/{stage}")

    # Process the chat message with resilient streaming
    status_code, complete_response = process_chat_message(connection_id, apigw_client, parameters, prompt)
    
    # Here you would typically save the complete_response to your thread/chat history
    # For now, just log it
    if complete_response:
        logger.info(f"Complete response generated: {len(complete_response)} characters")
        # TODO: Save to thread history database/storage
        # save_message_to_thread(user_prompt=prompt, ai_response=complete_response)

    return {"statusCode": status_code}