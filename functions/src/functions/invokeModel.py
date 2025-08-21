import boto3
import json
import os
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Defaults
DEFAULT_MODEL_ID = os.environ.get("DEFAULT_MODEL_ID","anthropic.claude-instant-v1")
AWS_REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
DEFAULT_MAX_TOKENS = 256
DEFAULT_TEMPERATURE = 0

# global variables - avoid creating a new client for every request
bedrock_client = None
apigw_client = None


def construct_request_body(modelId, parameters, prompt):
    # Handle inference profile ARNs
    if modelId.startswith("arn:aws:bedrock"):
        # Extract provider from inference profile ARN
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


def post_to_websockets(apig_management_client, connection_id, message):
    try:
        apig_management_client.post_to_connection(
            Data=message, ConnectionId=connection_id
        )
    except ClientError:
        logger.exception("Couldn't post to connection %s.", connection_id)
    except apig_management_client.exceptions.GoneException:
        logger.info("Connection %s is gone.", connection_id)


def call_llm(connection_id, apig_management_client, parameters, prompt):
    global bedrock_client

    status_code = 200
    modelId = parameters.pop("modelId", DEFAULT_MODEL_ID)

    body = construct_request_body(modelId, parameters, prompt)
    if body == None:
        error_msg = "Unsupported provider: " + modelId.split(".")[0]
        post_to_websockets(apig_management_client, connection_id, error_msg)
        status_code = 400
        return status_code
    logger.info(f"ModelId {modelId}, Body: {body}")

    if (bedrock_client is None):
        bedrock_client = boto3.client(service_name='bedrock-runtime', region_name=AWS_REGION)

    response = bedrock_client.invoke_model_with_response_stream(
        body=json.dumps(body), 
        modelId=modelId, 
        accept='application/json', 
        contentType='application/json'
    )
    stream = response.get('body')
    
    if stream:
        for event in stream:
            chunk = event.get('chunk')
            if chunk:
                try:
                    chunk_obj = json.loads(chunk.get('bytes').decode())
                    logger.info(f"Raw chunk for {modelId}: {chunk_obj}")
                    
                    # extract generated text based on model provider
                    generated_text = get_generated_text(modelId, chunk_obj)
                    
                    logger.info(f"Extracted text: '{generated_text}'")

                    if generated_text == None:
                        error_msg = "Unsupported provider: " + modelId.split(".")[0]
                        post_to_websockets(apig_management_client, connection_id, error_msg)
                        status_code = 400
                        return status_code

                    # Only send non-empty text to WebSockets
                    if generated_text:
                        post_to_websockets(apig_management_client, connection_id, generated_text)
                except Exception as e:
                    logger.error(f"Error processing chunk: {str(e)}, chunk: {chunk}")
                    error_msg = f"Error processing response: {str(e)}"
                    post_to_websockets(apig_management_client, connection_id, error_msg)
                    status_code = 500
                    return status_code

        # send a message to indicate end of LLM response
        end_msg = "<End of LLM response>"
        post_to_websockets(apig_management_client, connection_id, end_msg)
                
    return status_code


def handler(event, context):
    global apigw_client

    print("Event: ", json.dumps(event))

    # handle websockets request
    route_key = event.get("requestContext", {}).get("routeKey")
    connection_id = event.get("requestContext", {}).get("connectionId")
    if route_key is None or connection_id is None:
        return {"statusCode": 400}
    logger.info("Request: %s", route_key)

    # set default status code
    response = {"statusCode": 200}

    # extract information from event
    body = json.loads(event.get("body"))
    domain = event.get("requestContext", {}).get("domainName")
    stage = event.get("requestContext", {}).get("stage")
    prompt = body["prompt"]
    parameters = body["parameters"]

    if domain is None or stage is None:
        logger.warning(
            "Couldn't send message. Bad endpoint in request: domain '%s', "
            "stage '%s'",
            domain,
            stage,
        )
        response["statusCode"] = 400
    else:
        if apigw_client is None:
            apigw_client = boto3.client("apigatewaymanagementapi", endpoint_url=f"https://{domain}/{stage}")
        response["statusCode"] = call_llm(connection_id, apigw_client, parameters, prompt)

    return response