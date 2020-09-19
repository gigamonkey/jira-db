#!/usr/bin/env python3

import json
import os
import sys

from jira import JIRA


def issues(client, jql, fields=[]):
    "Fetch issues from Jira"
    start = 0
    while start is not None:
        r = client.search_issues(
            jql,
            startAt=start,
            maxResults=50,
            json_result=True,
            # fields=fields,
            # expand="changelog",
        )
        batch = r["issues"]
        start = start + len(batch) if start < r["total"] else None
        yield from batch


if __name__ == "__main__":

    url = os.environ["JIRA_URL"]
    account = os.environ["JIRA_ACCOUNT"]
    key = os.environ["JIRA_KEY"]
    client = JIRA(url, basic_auth=(account, key))

    fields = [
        "assignee",
        "changelog",
        "components",
        "created",
        "customfield_10003",
        "customfield_10006",
        "customfield_10008",
        "duedate",
        "issuetype",
        "parent",
        "project",
        "resolution",
        "resolutiondate",
        "status",
        "summary",
        "updated",
    ]

    for issue in issues(client, f"key = {sys.argv[1]}", fields=fields):
        json.dump(issue, fp=sys.stdout, indent=2)
