"""tools/mock_data.py — Test fixtures for --test mode"""
from datetime import date, timedelta
from core.normalizer import Assignment

def mock_assignments():
    today = date.today()
    from collections import defaultdict
    from core.normalizer import normalize_assignments, track_assignments
    raw = [
        Assignment("m001","7A-4-3-Homework1","Math","savvas",today-timedelta(6),False,None,25,"","in_progress"),
        Assignment("m002","7A-Topic4-HW","Math","savvas",today+timedelta(4),False,None,25,"","not_started"),
        Assignment("c001","Domain 6 Lesson 1","Career Tech","canvas",today+timedelta(3),False,None,15,"","unsubmitted"),
        Assignment("c002","Excel Practice Exam 2","Career Tech","canvas",today-timedelta(5),True,0,35,"","graded"),
        Assignment("s001","Lab Report Ch9","Science","canvas",today+timedelta(1),False,None,40,"","unsubmitted"),
        Assignment("s002","Chapter 7 Quiz","Science","canvas",today,False,None,20,"","unsubmitted"),
        Assignment("s003","Activity only if absent","Science","canvas",today-timedelta(10),False,None,15,"","unsubmitted",absent_only=True),
    ]
    cutoff = today - timedelta(days=60)
    normalized = normalize_assignments(raw, cutoff)
    return track_assignments(normalized), cutoff, ["Mock data"], []
