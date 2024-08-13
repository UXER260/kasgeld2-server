# Created by camillodejong at 14/08/2024 00:29

# DEZE FILE MOET GEÏMPORTEERD ZIJN VANAF `main.py` OM PROGRAMMA TE KUNNEN HERSTARTEN

import os
import sys


def restart_program():
    python = sys.executable
    os.execv(python, [python] + sys.argv)


def update_available() -> bool:
    # Fetch the latest changes from the remote repository
    os.system("git fetch --verbose origin")

    # Get the latest commit hash on the local and remote branches
    local_hash = os.popen("git rev-parse HEAD").read()
    remote_hash = os.popen("git rev-parse origin/master").read()

    print(local_hash)
    print(remote_hash)

    # Compare the hashes
    if local_hash != remote_hash:
        print("New version available.")
        return True
    else:
        print("Your local repository is up-to-date.")
        return False


def unconditional_pull_latest_repo():  # update no matter what
    update_available()
    print("Pulling the latest changes...")
    os.system("git merge origin/master")


def conditional_pull_latest_repo():  # update if available
    if update_available():
        unconditional_pull_latest_repo()
        return True
    else:
        print("Nothing to update.")


def unconditional_deploy_latest_update():
    unconditional_pull_latest_repo()
    restart_program()


def conditional_deploy_latest_update():
    if conditional_pull_latest_repo() is True:
        restart_program()
