# The python version to use is supplied as an arg from SST
ARG PYTHON_VERSION=3.11

# Use an official AWS Lambda base image for Python
FROM public.ecr.aws/lambda/python:${PYTHON_VERSION}

# Install the dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install -r requirements.txt

# Copy the rest of the code
COPY . ${LAMBDA_TASK_ROOT}

# No need to configure the handler or entrypoint - SST will do that
