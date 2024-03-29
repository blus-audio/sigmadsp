#!/bin/bash

OUTPUT_DIR=sigmadsp/generated/backend_service

echo "=== Building protobuf schemas..."

python3 -m grpc_tools.protoc -I schemas --python_out=$OUTPUT_DIR --grpc_python_out=$OUTPUT_DIR --mypy_out=$OUTPUT_DIR control.proto
