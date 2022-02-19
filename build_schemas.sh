#!/bin/sh

OUTPUT_DIR=src/sigmadsp/generated/backend_service/

echo "Building protobuf schemas..."

python3 -m grpc_tools.protoc -I schemas --python_out=$OUTPUT_DIR --grpc_python_out=$OUTPUT_DIR control.proto

echo "Built to output directory '$OUTPUT_DIR'."
