"""
savvas_connector.py — Savvas Realize GraphQL API connector

Token obtained by savvas_refresh_token.py (Playwright automation).
This file makes the actual GraphQL request and normalizes results.

Usage:
  from savvas_connector import fetch_savvas_assignments, normalize_savvas
  raw  = fetch_savvas_assignments(page_size=50)
  norm = normalize_savvas(raw)
"""

import os, requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

GRAPHQL_URL = "https://www.savvasrealize.com/graphql"

QUERY = """
query GetStudentAssignments($classId: String!, $studentId: String!, $pageSize: Int!) {
  getStudentClassAssignments(
    classId: $classId
    studentId: $studentId
    pageSize: $pageSize
  ) {
    totalCount
    items {
      id
      name
      dueDate
      completionStatus
      score
      maxScore
      url
    }
  }
}
"""

def fetch_savvas_assignments(page_size=50):
    token      = os.getenv("SAVVAS_TOKEN", "")
    class_id   = os.getenv("SAVVAS_CLASS_ID", "")
    student_id = os.getenv("SAVVAS_STUDENT_ID", "")

    if not all([token, class_id, student_id]):
        raise ValueError("SAVVAS_TOKEN, SAVVAS_CLASS_ID, SAVVAS_STUDENT_ID must be set in .env")

    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {"query": QUERY, "variables": {
        "classId": class_id, "studentId": student_id, "pageSize": page_size
    }}
    r = requests.post(GRAPHQL_URL, json=payload, headers=headers, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Savvas GraphQL HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"Savvas GraphQL errors: {data['errors']}")
    return data.get("data", {}).get("getStudentClassAssignments", {}).get("items", [])


def normalize_savvas(raw_items):
    out = []
    for item in raw_items:
        due_str = item.get("dueDate", "")
        try:
            due_d = datetime.fromisoformat(due_str.replace("Z", "+00:00")).date()
        except Exception:
            continue
        status    = (item.get("completionStatus") or "").lower()
        score     = item.get("score")
        max_sc    = item.get("maxScore") or 0
        submitted = status in ("completed", "submitted", "graded", "in_progress")
        out.append({
            "id":        str(item.get("id", "")),
            "title":     item.get("name", ""),
            "due_date":  due_d,
            "submitted": submitted,
            "score":     score,
            "points":    float(max_sc),
            "url":       item.get("url", ""),
            "workflow":  status,
        })
    return out
