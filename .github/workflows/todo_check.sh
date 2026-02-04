#!/bin/bash
FAIL=0  # Initialize the fail variable

for file in $CHANGED_FILES; do
  awk -v file="$file" '
    /TODO ☐/ {
      if (!reported) { printf("❌ Found TODO ☐ in %s\n", file); reported=1 }
      count++
      printf("%s:%d:%s\n", file, FNR, $0)
      inblock=1
      next
    }
    inblock && /^[[:space:]]*#/ {
      printf("%s:%d:%s\n", file, FNR, $0)
      next
    }
    inblock { inblock=0 }
    END { exit(count>0 ? 1 : 0) }
  ' "$file"
  if [ $? -ne 0 ]; then
    FAIL=1
  fi
done

if [ $FAIL -eq 1 ]; then
    echo "❌ TODO check failed."
    exit 1
else
    echo "✅ No TODO ☐ found in changed files."
    exit 0
fi
