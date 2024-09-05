# Created by camillodejong at 14/08/2024 00:29

# DEZE FILE IS BEDOELD GEÏMPORTEERD ZIJN VANAF `main.py` (OM PROGRAMMA TE KUNNEN HERSTARTEN)

import os
import sys


def restart_program():
    python = sys.executable
    os.execv(python, [python] + sys.argv)


def fetch_update():  # Fetch the latest changes from the remote repository
    print(os.popen("git fetch --verbose origin").read(), "aaa")


def update_available() -> bool:
    # Get the latest commit hash on the local and remote branches
    local_hash = os.popen("git rev-parse HEAD").read()
    remote_hash = os.popen("git rev-parse origin/master").read()

    print(local_hash)
    print(remote_hash)

    if local_hash != remote_hash:
        print("New version available.")
        return True
    else:
        print("Your local repository is up-to-date.")
        return False


def pull_latest_repo():  # update if available
    fetch_update()
    if update_available():
        print("Merging latest changes...")
        # zorg ervoor dat is ge-fetched voor git reset/merge/rebase
        print(os.popen("git reset --hard origin/master").read())
        return True
    else:
        print("Nothing to update.")
        return False


def deploy_latest_update():
    if pull_latest_repo() is True:
        restart_program()
