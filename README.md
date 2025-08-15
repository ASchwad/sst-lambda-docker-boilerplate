# ❍ AWS Python Container with PydanticAI

Deploy Python applications using SST with advanced AI capabilities powered by PydanticAI.

This project demonstrates how to deploy Python Lambda functions using SST's container mode, with a focus on AI-powered applications using PydanticAI for natural language processing and tool execution.

## 🚀 Features

- **PydanticAI Integration**: Advanced AI agent framework with natural language understanding
- **Calculator Tool**: Secure mathematical expression evaluation
- **Container Deployment**: Uses Docker containers for Lambda deployment
- **SST Framework**: Modern serverless deployment with SST
- **Python 3.11**: Optimized for AWS Lambda runtime

## 🏗️ Architecture

The project consists of two main components:

1. **`functions/`**: Main Lambda function with PydanticAI agent and calculator tool
2. **`custom_dockerfile/`**: Example of custom Dockerfile deployment

## 📁 Project Structure

```
.
├── functions/                    # Main Lambda function workspace
│   ├── pyproject.toml          # Python dependencies (pydantic-ai, openai)
│   ├── Dockerfile              # Custom container configuration
│   ├── src/functions/api.py    # PydanticAI agent implementation
│   └── requirements.txt        # Runtime dependencies for container
├── core/                        # Shared core functionality
├── custom_dockerfile/           # Custom Dockerfile example
├── sst.config.ts               # SST deployment configuration
└── pyproject.toml              # Root workspace configuration
```

## 🎯 PydanticAI Agent

The main function implements a PydanticAI agent that can:

- Understand natural language queries
- Execute mathematical calculations securely
- Provide intelligent responses using OpenAI's GPT models
- Handle complex tool interactions

### Example Usage

```bash
curl -X POST "https://your-function-url.lambda-url.region.on.aws/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is 2 + 2?"}'
```

**Response:**

```json
{
  "query": "What is 2 + 2?",
  "response": "The sum of 2 + 2 is 4.",
  "message": "PydanticAI Calculator Agent is working!"
}
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

- **Model**: OpenAI GPT-3.5-turbo
- **Tools**: Secure calculator with input validation
- **Security**: Mathematical expression validation to prevent code injection
- **Dependencies**: Managed via requirements.txt and installed in the container

## 📚 Dependencies

- `pydantic-ai`: AI agent framework
- `pydantic`: Data validation
- `openai`: OpenAI API integration

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

- The agent requires an OpenAI API key to be configured in your environment
- The calculator tool only supports basic mathematical operations for security
- All responses are returned as JSON with proper HTTP headers
- Dependencies are managed via `requirements.txt` and installed in the container
- SST workspace management requires `pyproject.toml` even when using `requirements.txt`

For more details, see the individual README files in each workspace directory.
