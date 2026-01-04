import asyncio
import httpx
from collections import defaultdict
from datetime import datetime, timezone

WDQS_ENDPOINT = "https://query.wikidata.org/sparql"
class WikidataBioFetcher:
    """
    A utility class to fetch and structure biography data for a person from Wikidata using SPARQL queries.
    """

    def __init__(self, user_agent: str = "WikidataBioFetcher/1.0 (contact: jovial@test.com)", timeout: int = 30):
        self.headers = {
            "User-Agent": user_agent
        }
        self.timeout = timeout
                
    async def fetch_person_data_for_bio(self, qid: str, language: str = "en") -> dict:
            """
            Return a structured biography JSON for a person (Wikidata item).
            - identity/core fields
            - lists (citizenship, occupation, etc.)
            - timeline lists with start/end/pointInTime (positions, teams, employers, education...)
            """
            qid = self._ensure_qid(qid)

            q_core = self._build_person_core_query(qid, language)
            q_lists = self._build_person_lists_query(qid, language)
            q_timeline = self._build_person_timeline_query(qid, language)

            core_json, lists_json, timeline_json = await asyncio.gather(
                self._wdqs(q_core),
                self._wdqs(q_lists),
                self._wdqs(q_timeline),
            )

            core = self._parse_core(core_json)
            lists = self._parse_kind_value_rows(lists_json)
            timeline = self._parse_timeline_rows(timeline_json)

            # Optional: sort timeline entries chronologically (best-effort)
            for k in timeline:
                timeline[k] = sorted(timeline[k], key=self._timeline_sort_key)

            result = {
                "id": core.get("id") or qid,
                "qid": self._qid_from_uri(core.get("id")) if core.get("id") else qid,
                "label": core.get("label"),
                "description": core.get("description"),
                "core": core,
                "lists": lists,
                "timeline": timeline,
            }

            # Optional: a compact text field for indexing/chunking (many RAG pipelines like this)
            result["rag_text"] = self._render_rag_text(result)

            return result

    # ---------- WDQS low-level ----------

    async def _wdqs(self, sparql: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            r = await client.post(
                WDQS_ENDPOINT,
                data={"query": sparql},
                params={"format": "json"},
            )
            r.raise_for_status()
            return r.json()

    # ---------- Query builders ----------

    def _build_person_core_query(self, qid: str, language: str = "en") -> str:
        lang = f"{language},en"
        return f"""
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX bd: <http://www.bigdata.com/rdf#>

            SELECT
            ?item ?itemLabel ?itemDescription
            ?dateOfBirth ?placeOfBirth ?placeOfBirthLabel
            ?dateOfDeath ?placeOfDeath ?placeOfDeathLabel
            ?givenName ?givenNameLabel
            ?familyName ?familyNameLabel
            ?nativeName
            ?gender ?genderLabel
            ?image
            WHERE {{
            BIND(wd:{qid} AS ?item)

            OPTIONAL {{ ?item wdt:P569 ?dateOfBirth . }}
            OPTIONAL {{ ?item wdt:P19  ?placeOfBirth . }}
            OPTIONAL {{ ?item wdt:P570 ?dateOfDeath . }}
            OPTIONAL {{ ?item wdt:P20  ?placeOfDeath . }}

            OPTIONAL {{ ?item wdt:P735 ?givenName . }}
            OPTIONAL {{ ?item wdt:P734 ?familyName . }}
            OPTIONAL {{ ?item wdt:P1559 ?nativeName . }}

            OPTIONAL {{ ?item wdt:P21 ?gender . }}
            OPTIONAL {{ ?item wdt:P18 ?image . }}

            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{lang}" . }}
            }}
            LIMIT 1
            """.strip()

    def _build_person_lists_query(self, qid: str, language: str = "en") -> str:
        """
        Returns rows: kind, value, valueLabel
        Add/remove UNION blocks as needed.
        """
        lang = f"{language},en"
        return f"""
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX bd: <http://www.bigdata.com/rdf#>

            SELECT ?kind ?value ?valueLabel WHERE {{
            BIND(wd:{qid} AS ?item)

            {{
                BIND("citizenship" AS ?kind)
                ?item wdt:P27 ?value .
            }}
            UNION {{
                BIND("occupation" AS ?kind)
                ?item wdt:P106 ?value .
            }}
            UNION {{
                BIND("field_of_work" AS ?kind)
                ?item wdt:P101 ?value .
            }}
            UNION {{
                BIND("language_spoken" AS ?kind)
                ?item wdt:P1412 ?value .
            }}
            UNION {{
                BIND("award" AS ?kind)
                ?item wdt:P166 ?value .
            }}
            UNION {{
                BIND("notable_work" AS ?kind)
                ?item wdt:P800 ?value .
            }}
            UNION {{
                BIND("spouse" AS ?kind)
                ?item wdt:P26 ?value .
            }}
            UNION {{
                BIND("child" AS ?kind)
                ?item wdt:P40 ?value .
            }}
            UNION {{
                BIND("member_of" AS ?kind)
                ?item wdt:P463 ?value .
            }}

            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{lang}" . }}
            }}
            """.strip()

    def _build_person_timeline_query(self, qid: str, language: str = "en") -> str:
        lang = f"{language},en"
        return f"""
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX p:   <http://www.wikidata.org/prop/>
            PREFIX ps:  <http://www.wikidata.org/prop/statement/>
            PREFIX pq:  <http://www.wikidata.org/prop/qualifier/>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX bd:  <http://www.bigdata.com/rdf#>

            SELECT
            ?kind
            ?value ?valueLabel
            ?start ?end ?pointInTime
            WHERE {{
            BIND(wd:{qid} AS ?item)

            # Positions held (P39)
            {{
                BIND("position_held" AS ?kind)
                ?item p:P39 ?stmt .
                ?stmt ps:P39 ?value .
                OPTIONAL {{ ?stmt pq:P580 ?start . }}
                OPTIONAL {{ ?stmt pq:P582 ?end . }}
                OPTIONAL {{ ?stmt pq:P585 ?pointInTime . }}
            }}
            UNION

            # Played for / member of sports team (P54)
            {{
                BIND("sports_team" AS ?kind)
                ?item p:P54 ?stmt .
                ?stmt ps:P54 ?value .
                OPTIONAL {{ ?stmt pq:P580 ?start . }}
                OPTIONAL {{ ?stmt pq:P582 ?end . }}
                OPTIONAL {{ ?stmt pq:P585 ?pointInTime . }}
            }}
            UNION

            # Coached team (P6087)  <-- ADD THIS
            {{
                BIND("coached_team" AS ?kind)
                ?item p:P6087 ?stmt .
                ?stmt ps:P6087 ?value .
                OPTIONAL {{ ?stmt pq:P580 ?start . }}
                OPTIONAL {{ ?stmt pq:P582 ?end . }}
                OPTIONAL {{ ?stmt pq:P585 ?pointInTime . }}
            }}
            UNION

            # Teams where this person is head coach (inverse P286)  <-- ADD THIS
            {{
                BIND("head_coach_of" AS ?kind)
                ?value p:P286 ?stmt .
                ?stmt ps:P286 ?item .
                OPTIONAL {{ ?stmt pq:P580 ?start . }}
                OPTIONAL {{ ?stmt pq:P582 ?end . }}
                OPTIONAL {{ ?stmt pq:P585 ?pointInTime . }}
            }}
            UNION

            # Employer (P108)
            {{
                BIND("employer" AS ?kind)
                ?item p:P108 ?stmt .
                ?stmt ps:P108 ?value .
                OPTIONAL {{ ?stmt pq:P580 ?start . }}
                OPTIONAL {{ ?stmt pq:P582 ?end . }}
                OPTIONAL {{ ?stmt pq:P585 ?pointInTime . }}
            }}
            UNION

            # Educated at (P69)
            {{
                BIND("educated_at" AS ?kind)
                ?item p:P69 ?stmt .
                ?stmt ps:P69 ?value .
                OPTIONAL {{ ?stmt pq:P580 ?start . }}
                OPTIONAL {{ ?stmt pq:P582 ?end . }}
                OPTIONAL {{ ?stmt pq:P585 ?pointInTime . }}
            }}

            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{lang}" . }}
            }}
            """.strip()

    # ---------- Parsing helpers ----------

    def _parse_core(self, wdqs_json: dict) -> dict:
        bindings = wdqs_json.get("results", {}).get("bindings", [])
        if not bindings:
            return {}

        b = bindings[0]
        return {
            "id": self._v(b, "item"),
            "label": self._v(b, "itemLabel"),
            "description": self._v(b, "itemDescription"),

            "dateOfBirth": self._v(b, "dateOfBirth"),
            "placeOfBirth": self._entity_obj(b, "placeOfBirth", "placeOfBirthLabel"),

            "dateOfDeath": self._v(b, "dateOfDeath"),
            "placeOfDeath": self._entity_obj(b, "placeOfDeath", "placeOfDeathLabel"),

            "givenName": self._entity_obj(b, "givenName", "givenNameLabel"),
            "familyName": self._entity_obj(b, "familyName", "familyNameLabel"),
            "nativeName": self._v(b, "nativeName"),

            "gender": self._entity_obj(b, "gender", "genderLabel"),
            "image": self._v(b, "image"),
        }

    def _parse_kind_value_rows(self, wdqs_json: dict) -> dict:
        """
        Input rows: kind, value, valueLabel
        Output: {kind: [{id, qid, label}, ...], ...}
        """
        out = defaultdict(list)
        for b in wdqs_json.get("results", {}).get("bindings", []):
            kind = self._v(b, "kind")
            value = self._v(b, "value")
            label = self._v(b, "valueLabel")
            if not kind or not value:
                continue
            out[kind].append({
                "id": value,
                "qid": self._qid_from_uri(value),
                "label": label,
            })
        # dedupe by id while preserving order
        return {k: self._dedupe_list(v, key="id") for k, v in out.items()}

    def _parse_timeline_rows(self, wdqs_json: dict) -> dict:
        """
        Input rows: kind, value, valueLabel, start, end, pointInTime
        Output: {kind: [{id,qid,label,start,end,pointInTime}, ...], ...}
        """
        out = defaultdict(list)
        for b in wdqs_json.get("results", {}).get("bindings", []):
            kind = self._v(b, "kind")
            value = self._v(b, "value")
            label = self._v(b, "valueLabel")
            if not kind or not value:
                continue
            out[kind].append({
                "id": value,
                "qid": self._qid_from_uri(value),
                "label": label,
                "start": self._v(b, "start"),
                "end": self._v(b, "end"),
                "pointInTime": self._v(b, "pointInTime"),
            })
        return {k: self._dedupe_list(v, key=("id", "start", "end", "pointInTime")) for k, v in out.items()}

    # ---------- RAG text (optional but useful) ----------

    def _render_rag_text(self, bio: dict) -> str:
        core = bio.get("core", {})
        lists = bio.get("lists", {})
        timeline = bio.get("timeline", {})

        def labels(kind):
            return [x.get("label") for x in lists.get(kind, []) if x.get("label")]

        lines = []
        if core.get("label", ""):
            lines.append(f"Name: {core.get('label')}")
        if core.get("description", ""):
            lines.append(f"Description: {core.get('description')}")

        if core.get("dateOfBirth", {}) or (core.get("placeOfBirth", {}) and core.get("placeOfBirth", {}).get("label", None)):
            lines.append(f"Born: {core.get('dateOfBirth')} in {core.get('placeOfBirth', {}).get('label')}")
        if core.get("dateOfDeath",{}) or (core.get("placeOfDeath", {}) and core.get("placeOfDeath", {}).get("label", None)):
            lines.append(f"Died: {core.get('dateOfDeath')} in {core.get('placeOfDeath', {}).get('label')}")

        if labels("citizenship"):
            lines.append("Citizenship: " + "; ".join(labels("citizenship")))
        if labels("occupation"):
            lines.append("Occupation: " + "; ".join(labels("occupation")))
        if labels("award"):
            lines.append("Awards: " + "; ".join(labels("award")))
        if labels("notable_work"):
            lines.append("Notable works: " + "; ".join(labels("notable_work")))

        # timeline (short)
        for kind in ["position_held", "sports_team", "employer", "educated_at"]:
            entries = timeline.get(kind, [])
            if not entries:
                continue
            formatted = []
            for e in entries[:30]:
                span = self._format_span(e.get("start"), e.get("end"), e.get("pointInTime"))
                formatted.append(f"{e.get('label')}{span}")
            lines.append(f"{kind}: " + "; ".join([x for x in formatted if x]))

        return "\n".join([l for l in lines if l])

    # ---------- Utility ----------

    def _ensure_qid(self, qid: str) -> str:
        qid = qid.strip()
        return qid if qid.startswith("Q") else f"Q{qid}"

    def _v(self, binding: dict, var: str):
        return binding.get(var, {}).get("value")

    def _entity_obj(self, b: dict, id_var: str, label_var: str) -> dict | None:
        entity_id = self._v(b, id_var)
        if not entity_id:
            return None
        return {
            "id": entity_id,
            "qid": self._qid_from_uri(entity_id),
            "label": self._v(b, label_var),
        }

    def _qid_from_uri(self, uri: str | None) -> str | None:
        if not uri:
            return None
        # ex: http://www.wikidata.org/entity/Q2338559
        if "/entity/" in uri:
            return uri.rsplit("/entity/", 1)[-1]
        return None

    def _dedupe_list(self, items, key):
        seen = set()
        out = []
        for it in items:
            if isinstance(key, tuple):
                k = tuple(it.get(x) for x in key)
            else:
                k = it.get(key)
            if k in seen:
                continue
            seen.add(k)
            out.append(it)
        return out

    def _timeline_sort_key(self, e: dict):
        sentinel = datetime.max.replace(tzinfo=timezone.utc)  # <- aware
        return (
            self._parse_date(e.get("start")) or sentinel,
            self._parse_date(e.get("pointInTime")) or sentinel,
            self._parse_date(e.get("end")) or sentinel,
            e.get("label") or "",
        )

    def _parse_date(self, s: str | None):
        if not s:
            return None
        try:
            # WDQS: 1972-01-05T00:00:00Z
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None

    def _format_span(self, start: str | None, end: str | None, pit: str | None) -> str:
        def y(d):
            if not d:
                return None
            return d[:4]
        if pit and not start and not end:
            return f" ({y(pit)})" if y(pit) else ""
        if start or end:
            return f" ({y(start) or ''}–{y(end) or ''})"
        return ""
    
async def main_m2():
    client = WikidataBioFetcher(user_agent="MyRAGBot/1.0 (contact: jovial@test.com)")
    bio = await client.fetch_person_data_for_bio("Q2338559", language="en")
    print(bio.keys())
    return bio
    #print(bio["timeline"])
    #print(bio["rag_text"])