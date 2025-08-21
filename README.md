# ❍ AWS Lambda Docker Boilerplate with WebSocket Streaming

Deploy Python Lambda functions using SST with WebSocket streaming for AWS Bedrock models.

This project demonstrates how to deploy Python Lambda functions using SST's container mode, with a focus on streaming responses from AWS Bedrock models via WebSocket connections.

## 🚀 Features

- **WebSocket Streaming**: Real-time streaming of AI model responses
- **AWS Bedrock Integration**: Support for multiple Bedrock models (Claude, Titan, Nova, etc.)
- **Container Deployment**: Uses Docker containers for Lambda deployment
- **SST Framework**: Modern serverless deployment with SST
- **Python 3.11**: Optimized for AWS Lambda runtime
- **Simplified Architecture**: Single endpoint without DynamoDB dependencies

## 🏗️ Architecture

The project consists of a simplified WebSocket architecture:

1. **WebSocket API Gateway**: Handles WebSocket connections
2. **Lambda Function**: Single `invokeModel` endpoint for streaming Bedrock responses

## 📁 Project Structure

```
.
├── functions/                    # Lambda function workspace
│   ├── pyproject.toml          # Python dependencies
│   ├── Dockerfile              # Custom container configuration
│   ├── src/functions/
│   │   ├── invokeModel.py      # Main streaming function
│   │   ├── api.py              # Additional API functionality
│   │   └── sst.py              # SST utilities
│   └── requirements.txt        # Runtime dependencies for container
├── sst.config.ts               # SST deployment configuration
├── test_websocket_client.py    # WebSocket testing client
└── pyproject.toml              # Root workspace configuration
```

## 🎯 WebSocket Streaming

The WebSocket endpoint supports streaming responses from AWS Bedrock models with:

- Real-time token streaming from various model providers
- Support for Claude, Titan, Nova, Llama, and other Bedrock models
- Automatic response format handling per model provider
- Error handling and connection management

### Example Usage

Connect to the WebSocket and send a message to the `invokeModel` route:

```python
import asyncio
import websockets
import json

async def test_streaming():
    uri = "wss://your-api-id.execute-api.region.amazonaws.com/$default"
    
    async with websockets.connect(uri) as websocket:
        message = {
            "action": "invokeModel",
            "prompt": "Tell me a short joke",
            "parameters": {
                "modelId": "amazon.titan-text-express-v1",
                "maxTokens": 100,
                "temperature": 0.7
            }
        }
        
        await websocket.send(json.dumps(message))
        
        # Listen for streaming tokens
        while True:
            response = await websocket.recv()
            print(response, end="")
            if "<End of LLM response>" in response:
                break

asyncio.run(test_streaming())
```

## 🚀 Deployment

```bash
# Deploy the entire application
sst deploy

# Deploy only specific components
sst deploy --target PythonFn
sst deploy --target PythonFnCustom
```

## 🔧 Configuration

The function uses:

- **Model**: AWS Bedrock with Claude 3.7 Sonnet
- **Tools**: Secure calculator with input validation
- **Security**: Mathematical expression validation to prevent code injection
- **Dependencies**: Managed via requirements.txt and installed in the container

### ⚠️ AWS Bedrock Model Access & Streaming Requirements

Before deploying, ensure you have the following:

1. **Model Access**: Request access to Bedrock models in AWS Bedrock Console:
   - Go to [AWS Bedrock Console → Model Access](https://console.aws.amazon.com/bedrock/home?region=eu-central-1#/modelaccess)
   - Enable access for models you want to use (Claude, Titan, Nova, etc.)
   - Wait for approval (usually instant for most models)

2. **Streaming-Capable Models**: Only use models that support streaming responses:
   - ✅ **Amazon Titan**: `amazon.titan-text-express-v1`, `amazon.titan-text-lite-v1`
   - ✅ **Amazon Nova**: `amazon.nova-pro-v1:0`, `amazon.nova-lite-v1:0`
   - ✅ **Anthropic Claude**: All Claude models support streaming
   - ✅ **Meta Llama**: `meta.llama3-2-3b-instruct-v1:0`, etc.
   - ✅ **Mistral**: `mistral.pixtral-large-2502-v1:0`

3. **Inference Profiles** (Recommended): For better availability across regions:
   - Example: `arn:aws:bedrock:eu-central-1:ACCOUNT:inference-profile/eu.anthropic.claude-3-7-sonnet-20250219-v1:0`
   - Requires permissions for both the inference profile AND underlying foundation models

**Note**: If you use a model that doesn't support streaming, the function will fail with a Bedrock API error. Always verify streaming support before deployment.

## 📚 Dependencies

- `pydantic-ai`: AI agent framework
- `pydantic`: Data validation
- `boto3`: AWS SDK for Bedrock integration

## 🔒 Security Features

- Input validation for mathematical expressions
- Restricted character set for calculations
- Error handling without exposing system details
- Secure API key management

## 🎓 Key Learnings & Best Practices

### 1. **Dependency Management Strategy**

- **Use `requirements.txt` for container deployments**: While `pyproject.toml` is great for development, `requirements.txt` is more reliable for Docker container builds
- **Keep `pyproject.toml` minimal**: SST requires it for workspace management, but don't include runtime dependencies
- **Separate build vs runtime dependencies**: Development tools in `pyproject.toml`, runtime packages in `requirements.txt`

### 2. **Docker Configuration**

- **Base image**: Use `public.ecr.aws/lambda/python:3.11` for AWS Lambda compatibility
- **Dependency installation**: Install from `requirements.txt` before copying application code
- **Build context**: SST copies the entire function directory, so structure your Dockerfile accordingly

### 3. **PydanticAI Integration**

- **Correct API usage**: Use `Agent('openai:gpt-3.5-turbo', system_prompt='...')` syntax
- **Tool registration**: Use `@agent.tool` decorator with `RunContext` as first parameter
- **Lazy initialization**: Create the agent within the handler to avoid module-level import issues
- **Error handling**: Wrap agent creation and execution in try-catch blocks

### 4. **SST Container Mode**

- **Workspace requirements**: Each function must have a `pyproject.toml` for SST workspace management
- **Container flag**: Set `python: { container: true }` in SST config
- **Handler path**: Use `functions/src/functions/api.handler` format
- **Function URLs**: Enable with `url: true` for HTTP access

### 5. **Troubleshooting Common Issues**

- **502 Bad Gateway**: Usually indicates function startup failure or import errors
- **Missing dependencies**: Ensure all packages are in `requirements.txt` and Dockerfile installs them
- **Import errors**: Check that runtime dependencies don't include development-only packages
- **Build context issues**: Verify Dockerfile paths match SST's build context

### 6. **Security Considerations**

- **Input validation**: Always validate and sanitize user inputs
- **API key management**: Use environment variables (hardcoded only for testing)
- **Tool restrictions**: Limit tool capabilities to prevent code injection
- **Error messages**: Don't expose internal system details in error responses

## 🎉 Getting Started

1. Clone the repository
2. Install dependencies: `uv sync`
3. Deploy: `sst deploy`
4. Test the agent with curl commands

## 🔍 Testing & Debugging

```bash
# Test the deployed function
curl -X POST "https://your-function-url.lambda-url.region.on.aws/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is 100 / 4?"}'

# Check deployment status
sst deploy --target PythonFn

# View logs (if available)
sst logs PythonFn
```

## 📝 Notes

- The agent uses AWS Bedrock (no API keys needed - uses IAM permissions)
- Requires AWS Bedrock model access to be enabled in the console
- The calculator tool only supports basic mathematical operations for security
- All responses are returned as JSON with proper HTTP headers
- Dependencies are managed via `requirements.txt` and installed in the container
- SST workspace management requires `pyproject.toml` even when using `requirements.txt`
- Uses Claude 3.7 Sonnet via EU inference profiles for cross-region reliability

For more details, see the individual README files in each workspace directory.
