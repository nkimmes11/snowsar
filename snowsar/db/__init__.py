"""Optional SQLAlchemy persistence layer.

Activated only when SNOWSAR_DATABASE_URL is set. Default dev/test
configuration keeps jobs in the in-process snowsar.jobs.store module.
"""
