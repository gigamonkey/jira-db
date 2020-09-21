"Miscelaneous functions for pulling stats from Jira."


import arrow

#
# Map the field names we want to use to the actual terrible names Jira
# uses. (True means the name is the same in Jira.)
#

jira_fields = {
    "assignee": True,
    "component": "components",
    "created": True,
    "due_date": "duedate",
    "epic": "customfield_10006",
    "issue_type": "issuetype",
    "label": "labels",
    "name": "customfield_10003",
    "parent": True,
    "rank": "customfield_10009",
    "resolution": True,
    "resolved": "resolutiondate",
    "size": "labels",
    "sprint": "customfield_10008",
    "status": True,
    "summary": True,
    "updated": True,
}

#
# Functions to extract the field value from an issue.
#


def field(*names, fn=None):
    fn = fn or (lambda x: x)

    def extract(issue):
        value = issue["fields"]
        for n in names:
            value = value.get(n)
            if value is None:
                break
        return fn(value)

    return extract


def timestamp(s):
    "Convert a timestame string to ISO in UTC."
    return arrow.get(s).to("utc").isoformat() if s else None


def extract_size(labels):
    sizes = set(labels) & {"Small", "Medium", "Large"}
    return list(sizes)[0] if len(sizes) > 0 else None


extractors = {
    "assignee": field("assignee", "displayName"),
    "components": field("components", fn=lambda cs: [c["name"] for c in cs]),
    "created": field("created", fn=timestamp),
    "due_date": field("duedate", fn=timestamp),
    "epic": field("customfield_10006"),
    "issue_type": field("issuetype", "name"),
    "key": lambda x: x["key"],
    "labels": field("labels"),
    "name": field("customfield_10003"),
    "parent": field("parent", "key"),
    "rank": field("customfield_10009"),
    "resolution": field("resolution", "name"),
    "resolved": field("resolutiondate", fn=timestamp),
    "size": field("labels", fn=extract_size),
    "sprints": field("customfield_10008", fn=lambda x: x or []),
    "status": field("status", "name"),
    "summary": field("summary"),
    "updated": field("updated", fn=timestamp),
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
