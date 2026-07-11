"""
Human Approval — SQLAlchemy ORM models.

No separate table here by design. Approval is a status transition on
Task (status, approved_at, approved_by) — see
app/modules/tasks/models.py — since an approval only ever concerns one
task and doesn't need its own history table for this project's scope.
"""
