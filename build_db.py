#!/usr/bin/env python3

import os
import sqlite3
import sys

from jira import JIRA

from jiralib import extract, issues, timestamp, changes

base = ["key", "summary", "assignee", "status", "created", "updated", "resolved", "resolution"]


tables = {
    "tasks": base + ["epic"],
    "epics": base + ["epic_name"],
    "subtasks": base + ["parent"],
    "task_sprints": ["key", "sprint"],
    "components": ["key", "component"],
    "sprints": ["name", "state", "start", "end", "complete"],
    "changelog": ["key", "time", "field", "old", "new"],
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


    sprints_seen = set()

    for issue in issues(client, jql, fields=sorted(query_fields)):
        key = extract("key", issue)
        issue_type = extract("issue_type", issue)

        if issue_type == "Task":
            insert_task(simple_record(issue, "tasks"))

            for sprint in extract("sprints", issue):
                insert_task_sprint([key, sprint["name"]])

                if sprint["id"] not in sprints_seen:
                    sprints_seen.add(sprint["id"])
                    insert_sprint(sprint_record(sprint))

        elif issue_type == "Epic":
            insert_epic(simple_record(issue, "epics"))

        elif issue_type == "Sub-task":
            insert_subtask(simple_record(issue, "subtasks"))

        for component in extract("components", issue):
            insert_component([key, component])

        for change in changes(issue):
            insert_change([change[k] for k in tables["changelog"]])

    conn.commit()


def create_table(cursor, table):

    fields = tables[table]
    jql = f"insert into {table} values ({', '.join(['?'] * len(fields))})"

    cursor.execute(f"drop table if exists {table}")
    cursor.execute(f"create table {table} ({', '.join(fields)})")

    def insert(row):
        assert len(row) == len(fields)
        cursor.execute(jql, row)

    return insert


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


if __name__ == "__main__":

    url = os.environ["JIRA_URL"]
    account = os.environ["JIRA_ACCOUNT"]
    key = os.environ["JIRA_KEY"]

    client = JIRA(url, basic_auth=(account, key))
    conn = sqlite3.connect("jira.db")

    make_tables(conn, client, f"project in ({', '.join(sys.argv[1:])})")

    conn.close()
