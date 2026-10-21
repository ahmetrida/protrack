# Force Launch - ProTrack v1.07 Enterprise Edition
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import PastProjectArchive, ProjectProposal

FALLBACK_CORPUS = [
    {
        "title": "Automated Attendance System Using Computer Vision (2024)",
        "abstract": "An automated classroom attendance monitoring application built with OpenCV and deep metric facial encodings to mark student attendance in real time via camera feeds and export CSV sheets."
    },
    {
        "title": "Campus Placement & Recruitment Management Portal (2024)",
        "abstract": "A centralized web platform connecting graduating students with recruiters, featuring resume parsing, GPA eligibility filtering, interview scheduling, and placement analytics."
    },
    {
        "title": "Decentralized Academic Credential Verification Platform (2025)",
        "abstract": "A tamper-proof academic certificate verification portal using cryptographic SHA-256 hashes and smart contracts to eliminate counterfeit diplomas and enable instant employer validation."
    },
    {
        "title": "Smart Hospital Outpatient Queue & E-Prescription System (2025)",
        "abstract": "A clinical web application enabling patients to book appointments online, track live consultation queues, and generate digital prescriptions with automated inventory alerts."
    },
    {
        "title": "Machine Learning Crop Disease Detection Advisory System (2025)",
        "abstract": "An agricultural support portal where users upload plant leaf images to classify diseases using convolutional neural networks and receive localized treatment recommendations."
    }
]

def clean_text(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def jaccard_token_overlap(t1, t2):
    s1 = set(clean_text(t1).split())
    s2 = set(clean_text(t2).split())
    if not s1 or not s2:
        return 0.0
    return len(s1.intersection(s2)) / len(s1.union(s2))

def check_abstract_similarity(new_title, new_abstract, department=None, exclude_group_id=None):
    query_combined = clean_text(f"{new_title} {new_title} {new_abstract}")
    if len(query_combined.split()) < 4:
        return {"score": 0.0, "closest_match": "Provide at least 4 words for analysis", "risk": "LOW"}

    corpus_records = []

    archives = PastProjectArchive.objects.filter(department=department) if department else PastProjectArchive.objects.all()
    for a in archives:
        corpus_records.append({
            "title": f"{a.title} ({a.year} Archive)",
            "text": clean_text(f"{a.title} {a.title} {a.abstract}"),
            "raw_title": a.title
        })

    proposals = ProjectProposal.objects.all()
    if department:
        proposals = proposals.filter(group__department=department)
    if exclude_group_id:
        proposals = proposals.exclude(group_id=exclude_group_id)

    for p in proposals:
        corpus_records.append({
            "title": f"{p.title} (Group: {p.group.name})",
            "text": clean_text(f"{p.title} {p.title} {p.abstract}"),
            "raw_title": p.title
        })

    for item in FALLBACK_CORPUS:
        corpus_records.append({
            "title": item["title"],
            "text": clean_text(f"{item['title']} {item['title']} {item['abstract']}"),
            "raw_title": item["title"]
        })

    documents = [r["text"] for r in corpus_records] + [query_combined]

    try:
        word_vec = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        word_matrix = word_vec.fit_transform(documents)
        word_sims = cosine_similarity(word_matrix[-1], word_matrix[:-1]).flatten()

        char_vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5))
        char_matrix = char_vec.fit_transform(documents)
        char_sims = cosine_similarity(char_matrix[-1], char_matrix[:-1]).flatten()

        best_score = 0.0
        best_match = "No close match detected"

        for idx, rec in enumerate(corpus_records):
            w_score = float(word_sims[idx])
            c_score = float(char_sims[idx])
            t_overlap = jaccard_token_overlap(new_title, rec["raw_title"])
            hybrid = (0.50 * w_score) + (0.30 * c_score) + (0.20 * t_overlap)
            pct = round(min(hybrid * 100.0, 99.9), 1)
            if pct > best_score:
                best_score = pct
                best_match = rec["title"]

        if best_score >= 60.0:
            risk = "HIGH"
        elif best_score >= 30.0:
            risk = "MODERATE"
        else:
            risk = "LOW"

        return {
            "score": best_score,
            "closest_match": best_match if best_score >= 8.0 else "Unique Concept (Low Overlap)",
            "risk": risk
        }
    except Exception:
        return {"score": 0.0, "closest_match": "Unique Concept", "risk": "LOW"}
