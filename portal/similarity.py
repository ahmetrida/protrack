import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import PastProjectArchive, ProjectProposal

DOMAIN_STOPWORDS = {
    'project', 'system', 'application', 'using', 'based', 'portal', 'web',
    'develop', 'proposed', 'aims', 'manage', 'management', 'user', 'users',
    'allow', 'allows', 'data', 'module', 'modules', 'platform', 'software'
}

def clean_and_normalize(text):
    text = (text or '').lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    tokens = [w for w in text.split() if len(w) > 2 and w not in DOMAIN_STOPWORDS]
    return " ".join(tokens)

def calculate_abstract_similarity(new_title, new_abstract, exclude_group_id=None):
    corpus_docs = []
    corpus_titles = []
    corpus_meta = []

    for item in PastProjectArchive.objects.all():
        combined = clean_and_normalize(f"{item.title} {item.title} {item.abstract}")
        corpus_docs.append(combined)
        corpus_titles.append(clean_and_normalize(item.title))
        corpus_meta.append((item.title, f"Archive ({item.batch_year})"))

    proposals = ProjectProposal.objects.all()
    if exclude_group_id:
        proposals = proposals.exclude(group_id=exclude_group_id)

    for prop in proposals:
        combined = clean_and_normalize(f"{prop.proposed_title} {prop.proposed_title} {prop.abstract_text}")
        corpus_docs.append(combined)
        corpus_titles.append(clean_and_normalize(prop.proposed_title))
        corpus_meta.append((prop.proposed_title, f"Active Batch ({prop.group.group_name})"))

    if not corpus_docs:
        return 0.0, "No archive records", "N/A", []

    query_doc = clean_and_normalize(f"{new_title} {new_title} {new_abstract}")
    query_title = clean_and_normalize(new_title)

    if not query_doc.strip():
        return 0.0, "Insufficient text", "N/A", []

    all_docs = corpus_docs + [query_doc]

    word_vec = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), sublinear_tf=True)
    word_mat = word_vec.fit_transform(all_docs)
    word_sims = cosine_similarity(word_mat[-1], word_mat[:-1]).flatten()

    char_vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True)
    char_mat = char_vec.fit_transform(all_docs)
    char_sims = cosine_similarity(char_mat[-1], char_mat[:-1]).flatten()

    q_words = set(query_doc.split())
    q_title_words = set(query_title.split())

    final_scores = []
    for idx in range(len(corpus_docs)):
        doc_words = set(corpus_docs[idx].split())
        title_words = set(corpus_titles[idx].split())

        jaccard_doc = len(q_words & doc_words) / max(len(q_words | doc_words), 1)
        jaccard_title = len(q_title_words & title_words) / max(len(q_title_words | title_words), 1)

        raw_score = (0.45 * word_sims[idx]) + (0.30 * char_sims[idx]) + (0.15 * jaccard_title) + (0.10 * jaccard_doc)
        calibrated = min(round(raw_score * 135, 1), 99.4)
        final_scores.append(calibrated)

    best_idx = int(max(range(len(final_scores)), key=lambda i: final_scores[i]))
    best_score = final_scores[best_idx]
    matched_title, matched_source = corpus_meta[best_idx]
    matched_keywords = sorted(list(q_words & set(corpus_docs[best_idx].split())))[:6]

    return best_score, matched_title, matched_source, matched_keywords
