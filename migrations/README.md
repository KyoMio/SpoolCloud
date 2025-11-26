# Migrations

Migrations are used to create and update the database schema. They are run automatically every time SpoolCloud starts.

To create a new migration, edit the tables as desired in `spoolcloud/database/models.py`, then start the SpoolCloud server to update your local sqlite database.

```bash
pdm run python -m spoolcloud.main
```

Stop the server once it's up.

Then, let Alembic automatically create a new migration file:
```bash
pdm run alembic revision -m "some title" --autogenerate
```

Go into the created migration and make sure it looks good, that the column changes etc are as desired. Format it with Black and Ruff. Commit.
