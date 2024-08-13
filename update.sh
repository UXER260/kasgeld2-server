#!/bin/bash

# Fetch the latest changes from the remote repository
git fetch --verbose origin

# Get the latest commit hash on the local and remote branches
LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/master)

echo "LOCAL $LOCAL_HASH"
echo "REMOTE $REMOTE_HASH"

# Compare the hashes
if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
    echo "New version available. Pulling the latest changes..."
    git pull --verbose origin master
else
    echo "Your local repository is up-to-date."
fi
