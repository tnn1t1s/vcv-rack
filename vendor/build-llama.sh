#!/bin/bash
# Build llama.cpp as a static library for use in VCV Rack plugins.
# Run once from the repo root: vendor/build-llama.sh
# Output: vendor/llama.cpp/build/libllama_full.a  (all objects merged)
#         vendor/llama.cpp/build/include/           (headers)

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LLAMA_DIR="$SCRIPT_DIR/llama.cpp"
TAG="b8646"

# Clone if not present
if [ ! -d "$LLAMA_DIR" ]; then
    echo "Cloning llama.cpp @ $TAG..."
    git clone --depth 1 --branch "$TAG" https://github.com/ggml-org/llama.cpp.git "$LLAMA_DIR"
else
    echo "llama.cpp already cloned at $LLAMA_DIR"
fi

BUILD_DIR="$LLAMA_DIR/build"
mkdir -p "$BUILD_DIR"
MACOS_TARGET="${MACOSX_DEPLOYMENT_TARGET:-11.0}"

echo "Configuring..."
cmake -S "$LLAMA_DIR" -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_OSX_DEPLOYMENT_TARGET="$MACOS_TARGET" \
    -DBUILD_SHARED_LIBS=OFF \
    -DGGML_METAL=ON \
    -DGGML_CUDA=OFF \
    -DGGML_BLAS=OFF \
    -DLLAMA_BUILD_TESTS=OFF \
    -DLLAMA_BUILD_EXAMPLES=OFF \
    -DLLAMA_BUILD_SERVER=OFF \
    -DLLAMA_CURL=OFF

echo "Building (this takes a few minutes)..."
cmake --build "$BUILD_DIR" --config Release --clean-first -j$(sysctl -n hw.logicalcpu)

# Merge all .a files into one for easy linking
echo "Merging static libs..."
rm -f "$BUILD_DIR/libllama_full.a"
ALL_LIBS=$(find "$BUILD_DIR" -name "*.a" ! -name "libllama_full.a" | tr '\n' ' ')
libtool -static -o "$BUILD_DIR/libllama_full.a" $ALL_LIBS

# Copy headers
INCLUDE_DIR="$BUILD_DIR/include"
mkdir -p "$INCLUDE_DIR"
cp "$LLAMA_DIR/include/llama.h"         "$INCLUDE_DIR/"
cp "$LLAMA_DIR/ggml/include"/*.h        "$INCLUDE_DIR/"

echo ""
echo "Done. Link with:"
echo "  -L\$(VENDOR)/llama.cpp/build -lllama_full"
echo "  -I\$(VENDOR)/llama.cpp/build/include"
echo "  deployment target: $MACOS_TARGET"
