import boto3
import logging
import os
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    from sst import Resource
    TABLE_NAME = Resource.WebSocketConnections.name
    logger.info(f"Using SST Resource, TABLE_NAME: {TABLE_NAME}")
except ImportError as e:
    # Fallback for when sst package is not available
    logger.info(f"SST import failed: {e}, using fallback")
    TABLE_NAME = os.environ.get("SST_Resource_WebSocketConnections_name") or "aws-python-websocket-dev-WebSocketConnectionsTable-cbxsdzzm"
except Exception as e:
    logger.info(f"SST Resource access failed: {e}, using fallback")
    TABLE_NAME = os.environ.get("SST_Resource_WebSocketConnections_name") or "aws-python-websocket-dev-WebSocketConnectionsTable-cbxsdzzm"

# global variables - avoid creating a new client for every request
table = None

def handler(event, context):
    global table
    
    logger.info(f"OnConnect event: {event}")
    logger.info(f"TABLE_NAME: {TABLE_NAME}")

    connection_id = event.get("requestContext", {}).get("connectionId")
    query_params = event.get("queryStringParameters") or {}
    user_name = query_params.get("name", "guest")
    
    logger.info(f"Connection ID: {connection_id}, User: {user_name}")
    
    if TABLE_NAME is None:
        logger.error("TABLE_NAME is None")
        return {"statusCode": 400}
        
    if connection_id is None:
        logger.error("connection_id is None")
        return {"statusCode": 400}

    if table is None:
        table = boto3.resource("dynamodb").Table(TABLE_NAME)
    logger.info("Use table %s.", table.name)

    status_code = 200
    try:
        table.put_item(Item={"connectionId": connection_id, "userName": user_name})
        logger.info("Added connection %s for user %s.", connection_id, user_name)
    except ClientError as e:
        logger.exception("Couldn't add connection %s for user %s.", connection_id, user_name)
        logger.error(f"DynamoDB error: {e}")
        status_code = 503

    return { 'statusCode': status_code, 'body': 'Connected.' }