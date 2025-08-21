/// <reference path="./.sst/platform/config.d.ts" />

/**
 * ## AWS Lambda Python container
 *
 * Python Lambda function that use large dependencies like `numpy` and `pandas`, can
 * hit the 250MB Lambda package limit. To work around this, you can deploy them
 * as a container image to Lambda.
 *
 * :::tip
 * Container images on Lambda have a limit of 10GB.
 * :::
 *
 * In this example, we deploy two functions as container image.
 *
 * ```ts title="sst.config.ts" {2-4}
 * const base = new sst.aws.Function("PythonFn", {
 *   python: {
 *     container: true,
 *   },
 *   handler: "./functions/src/functions/api.handler",
 *   runtime: "python3.11",
 *   link: [linkableValue],
 *   url: true,
 * });
 * ```
 *
 * Now when you run `sst deploy`, it uses a built-in Dockerfile to build the image
 * and deploy it. You'll need to have the Docker daemon running.
 *
 * :::note
 * You need to have the Docker daemon running locally.
 * :::
 *
 * To use a custom Dockerfile, you can place a `Dockerfile` in the root of the
 * uv workspace for your function.
 *
 * ```ts title="sst.config.ts" {5}
 * const custom = new sst.aws.Function("PythonFnCustom", {
 *   python: {
 *     container: true,
 *   },
 *   handler: "./custom_dockerfile/src/custom_dockerfile/api.handler",
 *   runtime: "python3.11",
 *   link: [linkableValue],
 *   url: true,
 * });
 * ```
 *
 * Here we have a `Dockerfile` in the `custom_dockerfile/` directory.
 *
 * ```dockerfile title="custom_dockerfile/Dockerfile"
 * # The python version to use is supplied as an arg from SST
 * ARG PYTHON_VERSION=3.11
 *
 * # Use an official AWS Lambda base image for Python
 * FROM public.ecr.aws/lambda/python:${PYTHON_VERSION}
 *
 * # ...
 * ```
 *
 * The project structure looks something like this.
 *
 * ```txt {5}
 * ├── sst.config.ts
 * ├── pyproject.toml
 * └── custom_dockerfile
 *     ├── pyproject.toml
 *     ├── Dockerfile
 *     └── src
 *         └── custom_dockerfile
 *             └── api.py
 * ```
 *
 * Locally, you want to set the Python version in your `pyproject.toml` to make sure
 * that `sst dev` uses the same version as `sst deploy`.
 */
export default $config({
  app(input) {
    return {
      name: "aws-python-websocket",
      removal: input?.stage === "production" ? "retain" : "remove",
      home: "aws",
    };
  },
  async run() {
    // DynamoDB table for WebSocket connections
    const connectionsTable = new sst.aws.Dynamo("WebSocketConnections", {
      fields: {
        connectionId: "string",
      },
      primaryIndex: { hashKey: "connectionId" },
    });

    // Create WebSocket API
    const webSocketApi = new sst.aws.ApiGatewayWebSocket("WebSocketApi");

    // OnConnect Lambda function
    const onConnectFunction = new sst.aws.Function("OnConnectFunction", {
      python: {
        container: true,
      },
      handler: "./functions/src/functions/onConnect.handler",
      runtime: "python3.11",
      link: [connectionsTable],
      permissions: [
        {
          actions: ["dynamodb:PutItem"],
          resources: [connectionsTable.arn],
        },
      ],
    });

    // OnDisconnect Lambda function
    const onDisconnectFunction = new sst.aws.Function("OnDisconnectFunction", {
      python: {
        container: true,
      },
      handler: "./functions/src/functions/onDisconnect.handler",
      runtime: "python3.11",
      link: [connectionsTable],
      permissions: [
        {
          actions: ["dynamodb:DeleteItem"],
          resources: [connectionsTable.arn],
        },
      ],
    });

    // InvokeModel Lambda function (main streaming function)
    const invokeModelFunction = new sst.aws.Function("InvokeModelFunction", {
      python: {
        container: true,
      },
      handler: "./functions/src/functions/invokeModel.handler",
      runtime: "python3.11",
      timeout: "5 minutes",
      link: [connectionsTable],
      permissions: [
        {
          actions: ["dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:GetItem"],
          resources: [connectionsTable.arn],
        },
        {
          actions: ["execute-api:ManageConnections"],
          resources: ["*"],
        },
        {
          actions: ["bedrock:InvokeModelWithResponseStream"],
          resources: [
            "arn:aws:bedrock:*::foundation-model/*",
            "arn:aws:bedrock:*:*:inference-profile/*"
          ]
        }
      ]
    });

    // ChatAgent Lambda function (simplified resilient streaming)
    const chatAgentFunction = new sst.aws.Function("ChatAgentFunction", {
      python: {
        container: true,
      },
      handler: "./functions/src/functions/chatAgent.handler",
      runtime: "python3.11",
      timeout: "5 minutes",
      permissions: [
        {
          actions: ["execute-api:ManageConnections"],
          resources: ["*"],
        },
        {
          actions: ["bedrock:InvokeModelWithResponseStream"],
          resources: [
            "arn:aws:bedrock:*::foundation-model/*",
            "arn:aws:bedrock:*:*:inference-profile/*"
          ]
        }
      ]
    });

    // Add routes to WebSocket API
    webSocketApi.route("$connect", onConnectFunction.arn);
    webSocketApi.route("$disconnect", onDisconnectFunction.arn);
    webSocketApi.route("invokeModel", invokeModelFunction.arn);
    webSocketApi.route("chatMessage", chatAgentFunction.arn);

    return {
      websocketUrl: webSocketApi.url,
      connectionsTable: connectionsTable.name,
    };
  },
});
