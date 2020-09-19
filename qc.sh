#!/bin/bash

sqlite3 jira.db <<EOF
select count(*) from tasks;
select count(*) from epics;
select count(*) from subtasks;
select count(*) from sprints;
select count(*) from task_sprints;
select count(*) from changelog;
select count(*) from components;
select count(*) from labels;
EOF
