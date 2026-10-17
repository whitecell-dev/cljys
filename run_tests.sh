#!/bin/bash

# Test runner for clj-to-ys.py transpiler
# Usage: ./run_tests.sh

INPUT_DIR="test_suite"
OUTPUT_DIR="results"
TRANSPILER="python3 clj-to-ys.py"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "Running transpiler tests"
echo "=========================================="
echo ""

# Track results
PASSED=0
FAILED=0

for clj_file in "$INPUT_DIR"/*.clj; do
  if [ -f "$clj_file" ]; then
    filename=$(basename "$clj_file" .clj)
    output_file="$OUTPUT_DIR/${filename}.ys"
    error_file="$OUTPUT_DIR/${filename}.error"

    echo "Testing: $filename"

    # Run transpiler
    $TRANSPILER "$clj_file" >"$output_file" 2>"$error_file"

    # A failure is either the transpiler or the runtime; `ys FILE` executes the
    # emitted YS, so this catches invalid output and runtime failures alike;
    # `ys -c` would only compile it.
    if [ -s "$error_file" ]; then
      reason="Transpiler error"
    elif ys "$output_file" >/dev/null 2>&1; then
      reason=""
    else
      reason="ys could not run the output"
    fi

    if [ -z "$reason" ]; then
      echo "  ✅ PASS - executes under ys"
      PASSED=$((PASSED + 1))
      rm -f "$error_file" # Clean up empty error file
    else
      echo "  ❌ FAIL - $reason"
      FAILED=$((FAILED + 1))
    fi
  fi
done

echo ""
echo "=========================================="
echo "Results: $PASSED passed, $FAILED failed"
echo "=========================================="

# List generated files
echo ""
echo "Generated YAMLScript files:"
ls -la "$OUTPUT_DIR"/*.ys 2>/dev/null || echo "  (none)"

# Show any errors
if [ $FAILED -gt 0 ]; then
  echo ""
  echo "Error details:"
  for err_file in "$OUTPUT_DIR"/*.error; do
    if [ -f "$err_file" ] && [ -s "$err_file" ]; then
      echo "--- $(basename "$err_file") ---"
      cat "$err_file"
      echo ""
    fi
  done
fi

# Exit on the verdict, not on the status of the last command run. Without this
# the script always exits 0 and silently swallows a failing case.
[ "$FAILED" -eq 0 ]
