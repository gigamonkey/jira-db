"Miscelaneous functions for pulling stats from Jira."

from re import compile

import arrow

#
# Because the Jira API is awesome, the values in the list of sprints a
# Task has been part of (a.k.a. customfield_10008) are rendered--in
# the middle of a JSON response--as strings that appears to have been
# produced by calling toString() on some Java object. So we tear that
# apart with some regexps to get at the actual values. So elegant!
#

sprint_re = compile(
    r"^com\.atlassian\.greenhopper\.service\.sprint\.Sprint@.*?\[(.*?)\]"
)

sprint_values_re = compile(r"(\w+)=(.*?)(?:,|$)")


def sprints(issue):
    "Extract the name of the sprints a Task has been added to."

    def g():
        for desc in issue.get("fields", {}).get("customfield_10008") or []:
            m = sprint_re.match(desc)
            if m:
                yield dict(sprint_values_re.findall(m.group(1)))

    return list(g())


#
# Map the field names we want to use to the actual terrible names Jira
# uses. (True means the name is the same in Jira.)
#
jira_fields = {
    "assignee": True,
    "component": "components",
    "created": True,
    "epic": "customfield_10006",
    "epic_name": "customfield_10003",
    "issue_type": "issuetype",
    "parent": True,
    "resolution": True,
    "resolved": "resolutiondate",
    "sprint": "customfield_10008",
    "status": True,
    "summary": True,
    "updated": True,
}

#
# Functions to extract the field value from an issue.
#
extractors = {
    "assignee": lambda x: (x["fields"]["assignee"] or {"displayName": None})["displayName"],
    "components": lambda x: [c["name"] for c in x["fields"]["components"]],
    "created": lambda x: timestamp(x["fields"]["created"]),
    "epic": lambda x: x["fields"].get("customfield_10006"),
    "epic_name": lambda x: x["fields"].get("customfield_10003"),
    "issue_type": lambda x: x["fields"]["issuetype"]["name"],
    "key": lambda x: x["key"],
    "parent": lambda x: x["fields"]["parent"]["key"],
    "resolution": lambda x: (x["fields"].get("resolution") or {"name": None})["name"],
    "resolved": lambda x: timestamp(x["fields"]["resolutiondate"]),
    "sprints": sprints,
    "status": lambda x: x["fields"]["status"]["name"],
    "summary": lambda x: x["fields"]["summary"],
    "updated": lambda x: timestamp(x["fields"]["updated"]),
}


def issues(client, jql, fields=[]):
    "Fetch issues from Jira"
    start = 0
    while start is not None:
        r = client.search_issues(
            jql,
            startAt=start,
            maxResults=50,
            json_result=True,
            fields=translate_fields(fields),
            expand="changelog",
        )
        batch = r["issues"]
        start = start + len(batch) if start < r["total"] else None
        yield from batch


def translate_fields(fields):
    "The Jira fields we need to request."

    def g():
        for f in fields:
            x = jira_fields.get(f)
            if x is not None:
                yield f if x is True else x

    return list(g())


def extract(field, issue):
    return extractors[field](issue)


def timestamp(s):
    "Convert a timestame string to ISO in UTC."
    return arrow.get(s).to("utc").isoformat() if s else None


def changes(issue):
    key = issue["key"]
    yield {
        "key": key,
        "time": timestamp(issue["fields"]["created"]),
        "field": "created",
        "old": None,
        "new": None,
    }

    for h in issue["changelog"]["histories"]:
        time = timestamp(h.get("created"))
        for item in h["items"]:
            old_value = item["fromString"]
            new_value = item["toString"]
            if old_value != new_value:
                yield {
                    "key": key,
                    "time": time,
                    "field": item["field"],
                    "old": old_value,
                    "new": new_value,
                }
