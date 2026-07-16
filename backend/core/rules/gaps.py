"""Groups GAP-mode questions by shared keyword -- read-only clustering for
M0.4b (see DESIGN.md's milestone table: "gaps grouping (read-only ok)",
explicitly NOT the live draft->approve flywheel, which is M3).

No embeddings, no LLM -- token-overlap union-find over a stopword-filtered
vocabulary, the same "simple and legible" philosophy as KeywordRetriever.
Any two gap questions sharing one significant word end up in the same
cluster, transitively, so a chain of paraphrases merges into one group
without a fixed list of themes to maintain.

Phase 1 sharpening (see interview-prep discussion): "GAP" as a single
AnswerMode was collapsing three different things into one operator-facing
bucket -- a genuine content gap ("do you have summer camp dates?"), an
off-topic question ("who is playing fifa finals?"), and non-language noise
("bla bla bla"). Classification happens ONLY here, at reporting time -- it
never touches AnswerMode, routing.py, or what the parent saw. See
GapCategory's docstring in models/ask.py for why that boundary matters.

Not solved here (by design, stated honestly): true non-English input (e.g.
"tame kem cho?") currently still falls to UNCLEAR, since separating "wrong
language" from "no real words at all" needs actual language identification,
not a wordlist. That is deliberately deferred to Phase 2 as its own
dependency, not smuggled in here as a heuristic that would silently misfire.
"""
from __future__ import annotations

from collections import Counter

from backend.models.ask import AnswerMode, GapCategory, GapGroup, QuestionLog

_STOPWORDS = {
    "a", "an", "the", "is", "are", "do", "does", "did", "you", "your", "i",
    "we", "have", "has", "had", "for", "there", "to", "of", "in", "on", "at",
    "and", "or", "my", "me", "can", "could", "will", "would", "if", "it",
    "its", "this", "that", "what", "when", "where", "how", "why", "who",
    "with", "about", "any", "all", "be", "been", "not", "get", "got",
}

# A moderate, hand-curated set of common English words -- NOT an exhaustive
# dictionary. Purpose: tell "bla bla bla" (zero real words) apart from a real
# sentence that happens to include a proper noun or acronym the list doesn't
# know ("fifa"). The classifier below tolerates a couple of unrecognized
# tokens rather than requiring 100% coverage -- see _REAL_WORD_RATIO_MIN.
_COMMON_WORDS = {
    "playing", "play", "played", "player", "players", "game", "games",
    "team", "teams", "match", "matches", "final", "finals", "tournament",
    "champion", "championship", "league", "score", "win", "won", "winner",
    "sport", "sports", "football", "soccer", "basketball", "baseball",
    "want", "wanted", "need", "needed", "come", "coming", "came", "going",
    "go", "goes", "went", "gone", "ask", "asked", "asking", "tell", "told",
    "know", "known", "knew", "think", "thought", "work", "worked",
    "working", "help", "helped", "look", "looked", "looking", "use",
    "used", "using", "find", "found", "give", "given", "gave", "take",
    "taken", "took", "make", "made", "making", "feel", "felt", "seem",
    "seemed", "leave", "left", "put", "keep", "kept", "let", "begin",
    "began", "show", "showed", "shown", "hear", "heard", "run", "running",
    "ran", "move", "moved", "live", "lived", "living", "believe",
    "believed", "bring", "brought", "happen", "happened", "happening",
    "write", "wrote", "written", "sit", "sat", "stand", "stood", "lose",
    "lost", "pay", "paid", "meet", "met", "include", "included",
    "continue", "continued", "set", "learn", "learned", "change",
    "changed", "lead", "understand", "understood", "watch", "watched",
    "follow", "followed", "stop", "stopped", "create", "created", "speak",
    "spoke", "spoken", "read", "allow", "allowed", "add", "added", "spend",
    "spent", "grow", "grew", "grown", "open", "opened", "walk", "walked",
    "offer", "offered", "remember", "remembered", "love", "loved",
    "consider", "considered", "appear", "appeared", "buy", "bought",
    "wait", "waited", "serve", "served", "send", "sent", "expect",
    "expected", "build", "built", "stay", "stayed", "fall", "fell",
    "fallen", "cut", "reach", "reached", "pass", "passed", "sell", "sold",
    "require", "required", "report", "reported", "decide", "decided",
    "pull", "pulled", "raise", "raised", "call", "called", "try", "tried",
    "hope", "hoped", "start", "started", "turn", "turned", "picking",
    "pick", "picked", "drop", "dropped", "bring", "brought",
    "time", "times", "year", "years", "people", "way", "ways", "day",
    "days", "man", "men", "thing", "things", "woman", "women", "life",
    "lives", "child", "children", "kid", "kids", "world", "school",
    "schools", "state", "states", "family", "families", "student",
    "students", "group", "groups", "country", "problem", "problems",
    "hand", "hands", "part", "parts", "place", "places", "case", "cases",
    "week", "weeks", "month", "months", "company", "system", "systems",
    "program", "programs", "question", "questions", "night", "nights",
    "point", "points", "home", "water", "room", "rooms", "mother",
    "area", "areas", "money", "story", "stories", "fact", "facts", "lot",
    "lots", "right", "rights", "study", "book", "books", "eye", "eyes",
    "job", "jobs", "word", "words", "business", "issue", "issues", "side",
    "sides", "kind", "kinds", "head", "heads", "house", "houses",
    "service", "services", "friend", "friends", "father", "fathers",
    "power", "hour", "hours", "line", "lines", "end", "ends", "member",
    "members", "law", "laws", "car", "cars", "city", "cities",
    "community", "name", "names", "president", "minute", "minutes",
    "idea", "ideas", "body", "information", "back", "parent", "parents",
    "face", "level", "levels", "office", "door", "doors", "health",
    "person", "people", "art", "history", "party", "parties", "result",
    "results", "morning", "reason", "reasons", "research", "girl", "girls",
    "guy", "guys", "moment", "moments", "air", "teacher", "teachers",
    "education", "food", "class", "classes", "care", "hospital", "letter",
    "letters", "floor", "floors", "form", "forms", "sign", "signed",
    "signature", "document", "documents",
    "good", "new", "first", "last", "long", "great", "little", "own",
    "other", "others", "old", "big", "high", "different", "small",
    "large", "next", "early", "young", "important", "few", "public",
    "bad", "same", "able", "sure", "sick", "well", "much", "many", "more",
    "most", "some", "such", "yes", "no", "please", "thanks", "hello",
    "hi", "today", "tomorrow", "yesterday", "morning", "afternoon",
    "evening", "here", "there", "now", "still", "also", "just", "only",
    "even", "really", "very", "too", "again", "back", "before", "after",
}

# Broader than the current handbook.md -- topics a childcare-center
# handbook COULD plausibly ever cover. A question overlapping this list but
# not the literal handbook text reads as a genuine content gap worth
# writing up; a question overlapping neither reads as off-topic.
_DOMAIN_VOCAB = {
    "tuition", "fee", "fees", "payment", "payments", "billing", "invoice",
    "discount", "autopay", "enrollment", "enroll", "enrolled", "register",
    "registration", "waitlist", "tour", "visit", "schedule", "hours",
    "calendar", "holiday", "holidays", "closed", "closure", "closures",
    "vacation", "break", "pickup", "dropoff", "drop-off", "release",
    "authorized", "authorization", "custody", "guardian", "parent",
    "parents", "family", "sibling", "siblings", "allergy", "allergies",
    "allergic", "medication", "medicine", "fever", "sick", "illness",
    "health", "doctor", "pediatrician", "immunization", "immunizations",
    "vaccine", "vaccines", "vaccination", "vaccinations", "screening",
    "screenings", "exam", "checkup", "form", "forms", "document",
    "documents", "signature", "signed", "nap", "naptime", "sleep",
    "lunch", "lunchtime", "snack", "snacks", "meal", "meals", "food",
    "breakfast", "diaper", "diapers", "potty", "toilet", "bathroom",
    "teacher", "teachers", "staff", "director", "classroom", "classrooms",
    "curriculum", "activity", "activities", "outdoor", "playground",
    "toy", "toys", "program", "programs", "camp", "summer", "infant",
    "infants", "toddler", "toddlers", "preschool", "kindergarten", "age",
    "ages", "birthday", "discipline", "behavior", "incident", "injury",
    "injured", "accident", "safety", "security", "emergency", "contact",
    "communication", "app", "portal", "photo", "photos", "update",
    "updates", "note", "notes", "milestone", "development", "weather",
    "rain", "snow", "closing", "opening", "reminder", "reminders",
    "compliance", "cycle", "due", "expire", "expires", "appointment",
    "appointments",
}

_REAL_WORD_RATIO_MIN = 0.4  # tolerate ~1-2 unrecognized tokens in a short question


def _tokens(text: str) -> set[str]:
    words = "".join(c if c.isalnum() else " " for c in text.lower()).split()
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _classify(tokens: set[str]) -> GapCategory:
    """Domain-vocab overlap is checked FIRST, not the general real-word
    ratio: a domain word ("summer", "lunchtime", "tuition") is itself proof
    of coherent, on-topic language, even if the rest of the sentence isn't
    in the generic common-word list. Only questions that miss the domain
    list fall through to the coherence check, which exists purely to tell
    "off-topic but real English" (fifa finals) apart from noise (bla bla)."""
    if not tokens:
        return GapCategory.UNCLEAR
    if tokens & _DOMAIN_VOCAB:
        return GapCategory.CONTENT_GAP
    real_word_count = sum(1 for t in tokens if t in _COMMON_WORDS)
    if (real_word_count / len(tokens)) < _REAL_WORD_RATIO_MIN:
        return GapCategory.UNCLEAR
    return GapCategory.OFF_TOPIC


def _cluster(
    members: list[QuestionLog], tokens: dict[str, set[str]], category: GapCategory,
) -> list[GapGroup]:
    """Union-find clustering, scoped to one category so an off-topic
    question can never merge into a content-gap theme just by sharing an
    incidental stopword-adjacent token."""
    parent = {q.id: q.id for q in members}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    ids = [q.id for q in members]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if tokens[ids[i]] & tokens[ids[j]]:
                union(ids[i], ids[j])

    clusters: dict[str, list[QuestionLog]] = {}
    for q in members:
        clusters.setdefault(find(q.id), []).append(q)

    groups: list[GapGroup] = []
    for cluster_members in clusters.values():
        shared: Counter[str] = Counter()
        for q in cluster_members:
            shared.update(tokens[q.id])
        theme = shared.most_common(1)[0][0].capitalize() if shared else "General"
        groups.append(GapGroup(
            theme=theme,
            category=category,
            count=len(cluster_members),
            questions=sorted(cluster_members, key=lambda q: q.ts, reverse=True),
        ))
    return groups


_CATEGORY_ORDER = {
    GapCategory.CONTENT_GAP: 0,
    GapCategory.OFF_TOPIC: 1,
    GapCategory.UNCLEAR: 2,
}


def group_gaps(questions: list[QuestionLog]) -> list[GapGroup]:
    gaps = [q for q in questions if q.mode == AnswerMode.GAP]
    tokens = {q.id: _tokens(q.text) for q in gaps}

    by_category: dict[GapCategory, list[QuestionLog]] = {}
    for q in gaps:
        by_category.setdefault(_classify(tokens[q.id]), []).append(q)

    groups: list[GapGroup] = []
    for category, members in by_category.items():
        groups.extend(_cluster(members, tokens, category))

    groups.sort(key=lambda g: (_CATEGORY_ORDER[g.category], -g.count))
    return groups
