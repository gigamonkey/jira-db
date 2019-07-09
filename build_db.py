#!/usr/bin/env python3

import json
import os
import sqlite3
import sys
import traceback

from jira import JIRA

from jiralib import extract, issues, timestamp

tables = {
    "tasks": {
        "jql": "type = Task",
        "fields": [
            "key",
            "summary",
            "status",
            "created",
            "updated",
            "resolved",
            "resolution",
            "epic",
        ],
    },
    "epics": {
        "jql": "type = Epic",
        "fields": [
            "key",
            "epic_name",
            "summary",
            "status",
            "created",
            "updated",
            "resolved",
            "resolution",
        ],
    },
    "subtasks": {
        "jql": "type = Sub-task",
        "fields": [
            "key",
            "summary",
            "status",
            "created",
            "updated",
            "resolved",
            "resolution",
            "parent",
        ],
    },
}


def make_table(conn, client, preamble, table, jql, fields):
    "Make a table in our SQLite database from the given query."

    cursor, insert = create_table(conn, table, fields)

    for issue in issues(client, f"{preamble} and {jql}", fields=fields):
        try:
            cursor.execute(insert, [extract(field, issue) for field in fields])
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            json.dump(issue, sys.stdout, indent=2)
            exit()

    conn.commit()


def make_task_sprints_table(conn, client, preamble):

    jql = f"{preamble} and type = Task"
    table_fields = ["key", "sprint"]
    query_fields = ["key", "sprints"]

    cursor, insert = create_table(conn, "task_sprints", table_fields)

    for issue in issues(client, jql, fields=query_fields):
        try:
            key = extract("key", issue)
            for sprint in extract("sprints", issue):
                cursor.execute(insert, [key, sprint["name"]])
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            json.dump(issue, sys.stdout, indent=2)
            exit()

    conn.commit()


def make_sprints_table(conn, client, preamble):

    jql = f"{preamble} and type = Task"
    table_fields = ["name", "state", "start", "end", "complete"]
    query_fields = ["sprints"]

    seen = set()

    cursor, insert = create_table(conn, "sprints", table_fields)
    for issue in issues(client, jql, fields=query_fields):
        for sprint in extract("sprints", issue):
            if sprint["id"] not in seen:
                seen.add(sprint["id"])
                cursor.execute(
                    insert,
                    [
                        sprint["name"],
                        sprint["state"],
                        timestamp(denull(sprint["startDate"])),
                        timestamp(denull(sprint["endDate"])),
                        timestamp(denull(sprint["completeDate"])),
                    ],
                )

    conn.commit()


def denull(s):
    "The Jira Sprint.toString() method strikes again!"
    return None if s == "<null>" else s


def create_table(conn, table, fields):
    cursor = conn.cursor()
    cursor.execute(f"drop table if exists {table}")
    cursor.execute(f"create table {table} ({', '.join(fields)})")
    return cursor, f"insert into {table} values ({', '.join(['?'] * len(fields))})"


if __name__ == "__main__":

    url = os.environ["JIRA_URL"]
    account = os.environ["JIRA_ACCOUNT"]
    key = os.environ["JIRA_KEY"]
    client = JIRA(url, basic_auth=(account, key))

    conn = sqlite3.connect("jira.db")

    projects = sys.argv[1:]
    preamble = f"project in ({', '.join(projects)})"

    for name, spec in tables.items():
        print(f"Making table {name}")
        make_table(conn, client, preamble, name, spec["jql"], spec["fields"])

    print(f"Making table task_sprints")
    make_task_sprints_table(conn, client, preamble)

    print(f"Making table sprints")
    make_sprints_table(conn, client, preamble)

    conn.close()
