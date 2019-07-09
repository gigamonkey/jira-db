To set things up:

```
pipenv install --dev
```

Creata a `.env` file with these lines (and appropriate values):

```
export JIRA_URL=<url of your Jira cloud instance>
export JIRA_ACCOUNT=<account to use; looks like an email address>
export JIRA_KEY=<a key you get somehow from Jira associated with the account>
```

To build the database, `jira.db` with tickets from the projects `FOO`, `BAR`, and `BAZ`:

```
pipenv run ./build_db.py FOO BAR BAZ
```

Then:

```
sqlite3 jira.db
```

and go to town!
