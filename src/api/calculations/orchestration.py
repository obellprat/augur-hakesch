from celery import group

from calculations.calculations import app


@app.task(name="launch_group", bind=True)
def launch_group(self, task_signatures):
    """Launch a group from serialized signatures and return its group id."""
    signatures = [app.signature(sig) for sig in task_signatures]
    grp = group(signatures).apply_async()
    grp.save()
    return {"group_id": grp.id}

