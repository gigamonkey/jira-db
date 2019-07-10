"Miscelaneous functions for pulling stats from Jira."

from re import compile

import arrow

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


def parse_sprint(s):
    m = parse_sprint.sprint_re.match(s)
    return dict(sprint_values_re.findall(m.group(1))) if m else None


def extract_sprints(value):
    return [s for s in (parse_sprint(s) for s in value) if s] if value else []


extractors = {
    "assignee": field("assignee", "displayName"),
    "components": field("components", fn=lambda cs: [c["name"] for c in cs]),
    "created": field("created", fn=timestamp),
    "epic": field("customfield_10006"),
    "epic_name": field("customfield_10003"),
    "issue_type": field("issuetype", "name"),
    "key": lambda x: x["key"],
    "parent": field("parent", "key"),
    "resolution": field("resolution", "name"),
    "resolved": field("resolutiondate", fn=timestamp),
    "sprints": field("customfield_10008", fn=extract_sprints),
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
