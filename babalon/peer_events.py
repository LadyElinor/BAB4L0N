"""One arrival per tick, due in that tick, in a synthetic local event packet."""
from .contracts import Invalid, fields, integer


EVENT_PROJECTION = "babalon.peer-job-events.v1"


def project_jobs(packet, source_hash, view):
    result = {"source_sha256": source_hash, "view": view, "pointer": "/jobs"}
    try:
        fields(packet, {"profile", "jobs"})
        jobs = packet["jobs"]
        if packet["profile"] != EVENT_PROJECTION or view != "timing" or type(jobs) is not list:
            raise Invalid("wrong job packet")
        integer(len(jobs), 1, 32)
        misses = 0
        for arrival, job in enumerate(jobs, 1):
            fields(job, {"arrived", "completed"})
            integer(job["arrived"], arrival, arrival)
            if job["completed"] is not None:
                integer(job["completed"], arrival, len(jobs))
            misses += job["completed"] != arrival
    except Invalid:
        return {**result, "status": "UNAVAILABLE", "reason": "incomplete_or_invalid_events"}
    return {**result, "status": "REPORTED", "facts": {"missed_deadlines": misses}}
