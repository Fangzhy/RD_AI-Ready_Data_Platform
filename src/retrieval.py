"""Compare lexical retrieval with exact entity constraints from published SQL links."""
from dataclasses import dataclass
import json
import re
from urllib.parse import urlencode

from sklearn.feature_extraction.text import TfidfVectorizer

from src.database import records
from src.governance import visible_documents
from src.taxonomy import CONCEPTS

ID_PATTERN = re.compile(r"\b(?:exp-[a-z0-9]+|doc-[a-z0-9]+|res-[a-z]+-[a-z0-9_-]+|s-[a-z0-9]+-\d+|c-\d+|as-[a-z]+)\b",re.I)
LOOKUP_WORDS = set("""what which show give find tell me is was the a an recorded reported synthetic
measurement measurements measured value result results reading readout report in for of from on and
compound experiment sample project assay current document please did record curated structured sql""".split())


@dataclass(frozen=True)
class Evidence:
    citation: str
    section: str
    text: str
    document_id: str
    version: int | None
    access_class: str
    source_link: str
    source_record_id: str
    entities: frozenset[str]
    mapping_version: str | None = None
    batch_id: str | None = None
    row_number: int | None = None

    @property
    def source_citation(self):
        if self.mapping_version is None:
            return self.citation
        return (f"{self.citation} · source row {self.source_record_id} · mapping {self.mapping_version}"
                f" · batch {self.batch_id} · data row {self.row_number}")


def constraints(question):
    """Resolve explicit entity IDs, named projects and controlled assay terms."""
    text = question.casefold()
    ids = set(ID_PATTERN.findall(text))
    remainder = ID_PATTERN.sub(" ",text)
    for system in ("alpha","beta"):
        if re.search(rf"\b{system}\b",remainder):
            ids.add(system)
            remainder = re.sub(rf"\b{system}\b"," ",remainder)
    for c in CONCEPTS.values():
        for term in sorted(set([c["term"],*c["aliases"].values()]), key=len, reverse=True):
            pattern = r"\b"+re.escape(term.casefold())+r"\b"
            if re.search(pattern,remainder):
                ids.add(c["id"].casefold())
                remainder = re.sub(pattern," ",remainder)
    recognized = bool(ids) and set(re.findall(r"[\w]+",remainder)) <= LOOKUP_WORDS
    return ids, recognized


def entity_keys(row):
    return frozenset(str(row[k]).casefold() for k in
                     ("source_system","experiment_id","compound_id","sample_id","assay_id","result_id"))


def document_chunks(db, role):
    chunks = []
    for doc in visible_documents(db,role):
        did, version = doc["document_id"], doc["version"]
        link = db.execute("""SELECT measurement_json FROM document_result
                             WHERE document_id=? AND version=?""",(did,version)).fetchone()
        if not link:
            continue
        row = json.loads(link["measurement_json"])
        entities = entity_keys(row) | {did.casefold()}
        for part in doc["body"].split("\n\n"):
            section, text = part.split("\n",1)
            chunks.append(Evidence(f"{did}/v{version}/{section}",section,text,did,version,doc["access_class"],
                                   "/assistant?"+urlencode({"document":did,"version":version}),
                                   row["source_record_id"], entities))
    return chunks


def search_measurements(db, *, experiment_id=None, source_system=None, batch_id=None, result_id=None):
    """Search current published measurements using the intersection of supplied filters."""
    filters = {"r.experiment_id": experiment_id, "r.source_system": source_system,
               "s.batch_id": batch_id, "r.result_id": result_id}
    active = [(column, value) for column, value in filters.items() if value]
    if not active:
        return []
    where = " AND ".join(f"{column} = ? COLLATE NOCASE" for column, _ in active)
    return records(db, f"""SELECT r.*, s.batch_id, s.row_number, d.quality_status, d.reasons
                    FROM curated_results r JOIN source_record s USING(source_record_id)
                    JOIN quality_decision d USING(source_record_id) WHERE {where}
                    ORDER BY r.source_system, s.batch_id, s.row_number""", [value for _, value in active])


def measurement_evidence(row):
    rid = row["result_id"]
    value = str(row["result_value"]).removesuffix(".0")
    sentence = (f"{rid} recorded {value} {row['result_unit']} for {row['compound_id']} "
                f"using {row['assay_name']} in {row['experiment_id']}.")
    locator = urlencode({"record":row["source_record_id"], "mapping_version":row["mapping_version"]})
    return Evidence(f"SQL/{rid}", "Measurement", sentence, "", None, "internal",
                    "/lineage?" + locator, row["source_record_id"], entity_keys(row),
                    row["mapping_version"], row["batch_id"], row["row_number"])


def sql_evidence(db, ids):
    result_ids = [key for key in ids if key.startswith("res-")]
    if len(result_ids) != 1 or any(k.startswith("doc-") for k in ids):
        return None
    matches = [row for row in search_measurements(db, result_id=result_ids[0]) if ids <= entity_keys(row)]
    return measurement_evidence(matches[0]) if len(matches) == 1 else None


def retrieve(db, question, role="reader", mode="aware"):
    if mode not in ("baseline","aware"):
        raise ValueError("Unknown retrieval mode")
    chunks = document_chunks(db,role)
    ids, _ = constraints(question)
    ranked = []
    if chunks and question.strip():
        vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b[\w-]+\b", sublinear_tf=True)
        features = vectorizer.fit_transform([c.text for c in chunks])
        scores = (features @ vectorizer.transform([question]).T).toarray().ravel()
        for chunk,score in zip(chunks,scores):
            if mode == "aware" and ids:
                if not ids <= chunk.entities:
                    continue
                score += 1 + 0.5 * (chunk.section == "Measurement")
            if score > 0:
                ranked.append((float(score),chunk))
    if mode == "aware":
        structured = sql_evidence(db,ids)
        if structured and (not ranked or re.search(r"\b(?:curated|sql|structured)\b",question,re.I)):
            ranked.append((4.0,structured))
    ranked.sort(key=lambda pair: (-pair[0],pair[1].citation))
    return [chunk for _,chunk in ranked[:5]]


def supported(question, hits):
    ids, recognized = constraints(question)
    if not recognized:
        return []
    candidates = [e for e in hits if e.section=="Measurement" and ids <= e.entities]
    if re.search(r"\b(?:curated|sql|structured)\b",question,re.I):
        candidates = [e for e in candidates if e.citation.startswith("SQL/")]
    # A lookup with several different observations needs a more specific identifier.
    return candidates[:1] if len({e.source_record_id for e in candidates}) == 1 else []


INSUFFICIENT = "Insufficient evidence for this question. Try a single experiment, result, or report ID and ask for its recorded measurement."
