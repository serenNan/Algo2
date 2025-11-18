#!/bin/bash
# Basic functionality test for Enhanced CCA

set -e

FOGGYTCP_DIR="/home/serennan/work/algo2/enhanced_cca/foggytcp"
TEST_FILE="/home/serennan/work/algo2/foggytcp2/testdata/test_1mb.bin"
OUTPUT_FILE="/tmp/enhanced_cca_output.bin"

cd "$FOGGYTCP_DIR"

echo "=== Enhanced CCA Basic Test ==="
echo "Test file: $TEST_FILE ($(du -h $TEST_FILE | cut -f1))"
echo ""

# Clean up previous output
rm -f "$OUTPUT_FILE"

# Start server in background (using 0.0.0.0 to listen on all interfaces)
echo "Starting server on port 15441..."
./server 0.0.0.0 15441 "$OUTPUT_FILE" > /tmp/server.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to be ready
sleep 2

# Run client
echo "Starting client to send test file..."
START_TIME=$(date +%s.%N)
timeout 15 ./client 127.0.0.1 15441 "$TEST_FILE" > /tmp/client.log 2>&1
CLIENT_EXIT=$?
END_TIME=$(date +%s.%N)

if [ $CLIENT_EXIT -eq 124 ]; then
    echo "ERROR: Client timeout after 15 seconds"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Calculate transfer time
TRANSFER_TIME=$(echo "$END_TIME - $START_TIME" | bc)
FILE_SIZE=$(stat -c%s "$TEST_FILE")
THROUGHPUT=$(echo "scale=2; $FILE_SIZE / $TRANSFER_TIME / 1024 / 1024" | bc)

echo ""
echo "=== Test Results ==="
echo "Transfer time: ${TRANSFER_TIME}s"
echo "File size: $FILE_SIZE bytes"
echo "Throughput: ${THROUGHPUT} MB/s"

# Verify file integrity
if [ -f "$OUTPUT_FILE" ]; then
    ORIGINAL_MD5=$(md5sum "$TEST_FILE" | cut -d' ' -f1)
    RECEIVED_MD5=$(md5sum "$OUTPUT_FILE" | cut -d' ' -f1)

    echo ""
    echo "=== File Integrity Check ==="
    echo "Original MD5:  $ORIGINAL_MD5"
    echo "Received MD5:  $RECEIVED_MD5"

    if [ "$ORIGINAL_MD5" = "$RECEIVED_MD5" ]; then
        echo "✓ File transfer successful!"
    else
        echo "✗ File integrity check failed!"
        exit 1
    fi
else
    echo "✗ Output file not created!"
    exit 1
fi

# Cleanup
kill $SERVER_PID 2>/dev/null || true
sleep 1

echo ""
echo "=== Server Log (last 20 lines) ==="
tail -20 /tmp/server.log

echo ""
echo "=== Client Log (last 20 lines) ==="
tail -20 /tmp/client.log

echo ""
echo "Test completed successfully!"
