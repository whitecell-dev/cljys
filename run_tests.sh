#!/bin/bash

# Test runner for clj_to_ys.py transpiler
# Usage: ./run_tests.sh

INPUT_DIR="test_primitives"
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

    # Check if transpiler succeeded (no error output)
    if [ ! -s "$error_file" ]; then
      # Also check if output is valid YAMLScript (ys -c)
      if ys "$output_file" >/dev/null 2>&1; then
        echo "  ✅ PASS - Valid YAMLScript"
        PASSED=$((PASSED + 1))
        rm -f "$error_file" # Clean up empty error file
      else
        echo "  ❌ FAIL - YS compilation error"
        FAILED=$((FAILED + 1))
      fi
    else
      echo "  ❌ FAIL - Transpiler error"
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
