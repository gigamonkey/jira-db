#!/usr/bin/env python3

import os
import sqlite3
import sys

import arrow
from jira import JIRA

from jiralib import changes, extract, issues, timestamp

epoch = "1970-01-01T00:00:00+00:00"

base = [
    "key",
    "summary",
    "assignee",
    "status",
    "created",
    "updated",
    "resolved",
    "resolution",
    "due_date",
]


tables = {
    "tasks": base + ["epic"],
    "epics": base + ["epic_name"],
    "subtasks": base + ["parent"],
    "task_sprints": ["key", "sprint"],
    "components": ["key", "component"],
    "sprints": ["name", "state", "start", "end", "complete"],
    "changelog": ["key", "time", "field", "old", "new"],
    "highwater": ["time"],
}

table_keys = {
    "tasks": {"key"},
    "epics": {"key"},
    "subtasks": {"key"},
    "task_sprints": set(),
    "components": set(),
    "sprints": {"name"},
    "changelog": set(),
    "highwater": set(),
}


# fields we need to ask for from Jira (after being translated by jiralib).
query_fields = {"issue_type"}
for fields in tables.values():
    query_fields.update(fields)


def make_tables(conn, client, jql):
    "Do one big query for all issues and fill out a bunch of tables."

    cursor = conn.cursor()

    insert_task = create_table(cursor, "tasks")
    insert_epic = create_table(cursor, "epics")
    insert_subtask = create_table(cursor, "subtasks")
    insert_task_sprint = create_table(cursor, "task_sprints")
    insert_sprint = create_table(cursor, "sprints")
    insert_component = create_table(cursor, "components")
    insert_change = create_table(cursor, "changelog")
    insert_highwater = create_table(cursor, "highwater")

    sprints_seen = set()

    highwater = None

    count = 0
    for issue in issues(client, jql, fields=sorted(query_fields)):
        count += 1
        key = extract("key", issue)
        issue_type = extract("issue_type", issue)

        if issue_type == "Task":
            insert_task(simple_record(issue, "tasks"))

            cursor.execute("delete from task_sprints where key = ?", [key])
            for sprint in extract("sprints", issue):
                insert_task_sprint([key, sprint["name"]])

                if sprint["id"] not in sprints_seen:
                    sprints_seen.add(sprint["id"])
                    insert_sprint(sprint_record(sprint))

        elif issue_type == "Epic":
            insert_epic(simple_record(issue, "epics"))

        elif issue_type == "Sub-task":
            insert_subtask(simple_record(issue, "subtasks"))

        cursor.execute("delete from components where key = ?", [key])
        for component in extract("components", issue):
            insert_component([key, component])

        cursor.execute("delete from changelog where key = ?", [key])
        for change in changes(issue):
            insert_change([change[k] for k in tables["changelog"]])

        highwater = max(highwater or epoch, extract("updated", issue))

    if highwater:
        insert_highwater([highwater])

    conn.commit()
    print(f"Updated {count} issue(s).")


def create_table(cursor, table):

    fields = tables[table]
    keys = table_keys[table]

    jql = f"insert or replace into {table} values ({', '.join(['?'] * len(fields))})"

    cursor.execute(f"create table if not exists {table} ({schema(fields, keys)})")

    def insert(row):
        assert len(row) == len(fields)
        cursor.execute(jql, row)

    return insert


def schema(fields, keys):
    return ", ".join(f"{f} primary key" if f in keys else f for f in fields)


def simple_record(issue, table):
    return [extract(field, issue) for field in tables[table]]


def sprint_record(sprint):
    return [
        sprint["name"],
        sprint["state"],
        timestamp(denull(sprint["startDate"])),
        timestamp(denull(sprint["endDate"])),
        timestamp(denull(sprint["completeDate"])),
    ]


def denull(s):
    "The Jira Sprint.toString() method strikes again!"
    return None if s == "<null>" else s


def find_highwater(conn):
    cursor = conn.cursor()
    cursor.execute(
        "select name from sqlite_master where type='table' and name='highwater'"
    )
    if cursor.fetchone():
        cursor.execute("select max(time) from highwater")
        time = cursor.fetchone()[0]
    else:
        time = epoch

    # FIXME: Should really fetch the default timezone from the server.
    return arrow.get(time).to("US/Eastern").format("YYYY-MM-DD HH:mm")


if __name__ == "__main__":

    url = os.environ["JIRA_URL"]
    account = os.environ["JIRA_ACCOUNT"]
    key = os.environ["JIRA_KEY"]

    client = JIRA(url, basic_auth=(account, key))
    conn = sqlite3.connect("jira.db")

    projects = ", ".join(sys.argv[1:])
    highwater = find_highwater(conn)
    jql = f'project in ({projects}) and updated >= "{highwater}"'

    make_tables(conn, client, jql)

    conn.close()
