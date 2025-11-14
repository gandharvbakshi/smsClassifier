#!/bin/bash
# Copy ONNX models and feature vocab to Android assets folder

SOURCE_DIR="../android_model_exports"
TARGET_DIR="app/src/main/assets"

mkdir -p "$TARGET_DIR"

echo "Copying ONNX models..."
cp "$SOURCE_DIR/model_phishing.onnx" "$TARGET_DIR/" || echo "Warning: model_phishing.onnx not found"
cp "$SOURCE_DIR/model_isotp.onnx" "$TARGET_DIR/" || echo "Warning: model_isotp.onnx not found"
cp "$SOURCE_DIR/model_intent.onnx" "$TARGET_DIR/" || echo "Warning: model_intent.onnx not found"

echo "Copying feature vocab..."
cp "$SOURCE_DIR/model_metadata.json" "$TARGET_DIR/" || echo "Warning: model_metadata.json not found"

echo "Done! Models copied to $TARGET_DIR"

