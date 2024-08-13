# Created by camillodejong at 13/08/2024 14:50
import os
import json
with open("server/config.json") as f:
    config = json.load(f)

os.system("git fetch --verbose origin")

# Get the latest commit hash on the local and remote branches
local_hash = os.popen("git rev-parse HEAD").read().strip()
remote_hash = os.popen("git rev-parse origin/master").read().strip()

print("local_hash", local_hash)
print("remote_hash", remote_hash)

# Compare the hashes
if local_hash != remote_hash:
    print("New version available. Pulling the latest changes and restarting")
    os.system("git pull --verbose origin master")

    pid_location = "server/" + config["pid_location"]
    with open(pid_location) as f:
        os.system(f"kill {f.read()}")
        os.system("cd server && python3 main.py")
else:
    print("Your local repository is up-to-date.")
