import json
import boto3
from typing import Any, Dict
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


class CalculatorInput(BaseModel):
    expression: str = Field(description="Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5')")


class CalculatorOutput(BaseModel):
    result: float = Field(description="The calculated result")
    expression: str = Field(description="The original expression that was evaluated")


def calculator_tool(expression: str) -> CalculatorOutput:
    """Evaluate a mathematical expression safely."""
    try:
        # Only allow basic mathematical operations for security
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Expression contains invalid characters")
        
        # Evaluate the expression
        result = eval(expression)
        
        if not isinstance(result, (int, float)):
            raise ValueError("Result is not a number")
            
        return CalculatorOutput(result=float(result), expression=expression)
    except Exception as e:
        raise ValueError(f"Error evaluating expression '{expression}': {str(e)}")


def create_agent():
    """Create the agent with the calculator tool."""
    try:
        # Create a simple agent with AWS Bedrock
        agent = Agent(
            'bedrock:eu.anthropic.claude-3-7-sonnet-20250219-v1:0',
            system_prompt='You are a helpful calculator agent. When asked to calculate something, use the calculator tool to evaluate mathematical expressions safely.'
        )
        
        # Register the calculator tool using the decorator pattern
        @agent.tool
        def calculate(ctx: RunContext, expression: str) -> CalculatorOutput:
            """Evaluate a mathematical expression safely."""
            return calculator_tool(expression)
        
        return agent
    except Exception as e:
        print(f"Error creating agent: {e}")
        return None


def handler(event, context):
    try:
        # Parse the incoming request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract the query from the request
        query = body.get('query', 'What is 2 + 2?')
        
        # Create the agent (lazy initialization)
        agent = create_agent()
        if agent is None:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Failed to create agent"})
            }
        
        # Run the agent with the query
        response = agent.run_sync(query)
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "query": query,
                "response": response.output,
                "message": "PydanticAI Calculator Agent is working!"
            })
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": str(e),
                "message": "Error occurred while processing request"
            })
        }
