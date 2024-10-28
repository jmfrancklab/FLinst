#!/bin/bash
if git diff --name-only | xargs grep -l "TODO ☐"; then
    echo "❌ Found TODO ☐ in one or more files."
    exit 1
else
    echo "✅ No TODO ☐ found."
fi
