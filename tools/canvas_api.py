"""tools/canvas_api.py — Canvas REST API wrapper"""
import os, requests
from core.normalizer import Assignment, is_absent_only
from datetime import datetime

def fetch_canvas(course_id, course_name):
    token = os.getenv("CANVAS_TOKEN","")
    base  = os.getenv("CANVAS_URL","")
    try:
        r = requests.get(
            f"{base}/api/v1/courses/{course_id}/assignments?include[]=submission&per_page=100",
            headers={"Authorization": f"Bearer {token}"}, timeout=15
        )
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}", "assignments": []}
        raw = r.json()
    except Exception as e:
        return {"ok": False, "error": str(e), "assignments": []}

    out = []
    for a in raw:
        due_str = a.get("due_at")
        if not due_str: continue
        try:
            due_d = datetime.fromisoformat(due_str.replace("Z","+00:00")).date()
        except: continue
        sub  = a.get("submission") or {}
        name = a.get("name","")
        out.append(Assignment(
            id=str(a.get("id","")), title=name, course=course_name, source="canvas",
            due_date=due_d, submitted=sub.get("submitted_at") is not None,
            score=sub.get("score"), points=a.get("points_possible") or 0,
            url=a.get("html_url",""), workflow=sub.get("workflow_state",""),
            absent_only=is_absent_only(name), optional="optional" in name.lower()
        ))
    return {"ok": True, "assignments": out, "error": None}
