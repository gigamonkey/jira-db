#!/usr/bin/env python3

import json
import os
import sys

from jira import JIRA

from jiralib import issues

if __name__ == "__main__":

    url = os.environ["JIRA_URL"]
    account = os.environ["JIRA_ACCOUNT"]
    key = os.environ["JIRA_KEY"]
    client = JIRA(url, basic_auth=(account, key))

    for issue in issues(client, f"key = {sys.argv[1]}"):
        json.dump(issue, fp=sys.stdout, indent=2)
