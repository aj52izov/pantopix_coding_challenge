import httpx
from utils.logger import Logger
import re
from datetime import datetime

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WDQS_URL = "https://query.wikidata.org/sparql"

_QID_RE = re.compile(r"^Q\d+$")
_PID_RE = re.compile(r"^P\d+$")

class WikidataClient:
    def __init__(self, user_agent: str, timeout: float = 30.0):
        self._headers = {
            "User-Agent": user_agent,
        }
        self._timeout = timeout
        self.logger = Logger(__name__)
        
    async def _search_(self, text: str, type:str, language: str = "en", limit: int = 5) -> list[dict]:
        """
        Search on  Wikidata by text using wbsearchentities.
        Returns a list of candidates with fields like id, label, description.
        """
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "search": text,
            "language": language,
            "limit": limit,
            "type": type,
        }                
        async with httpx.AsyncClient(timeout=self._timeout, headers=self._headers) as client:
            r = await client.get(WIKIDATA_API, params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("search", [])

    async def search_entity(self, text: str, language: str = "en", limit: int = 5) -> list[dict]:
        """
        Search Wikidata items (Q-ids) by text using wbsearchentities.
        Returns a list of candidates with fields like id, label, description.
        """
        return await self._search_(text, type="item", language=language, limit=limit)

    async def search_property(self, text: str, *, language: str = "en", limit: int = 10) -> list[dict]:
        """
        Search Wikidata properties (P-ids) by text using wbsearchentities.
        """
        return await self._search_(text, type="property", language=language, limit=limit)

    async def wdqs_post(self, query: str) -> dict:
        """
        Run SPARQL query against WDQS using POST and return SPARQL JSON results.
        """
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": self._headers["User-Agent"],
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        data = {"query": query}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(WDQS_URL, headers=headers, data=data)
            r.raise_for_status()
            return r.json()
        
    def _ensure_qid(self, qid: str) -> str:
        """
         check q-id format.
         
         ags:
            pid: The q-id to validate (e.g., "Q524").
         Returns:
            q-id.
        Raises:
            ValueError: If the q-id format is invalid.
        """
        if not _QID_RE.match(qid):
            raise ValueError(f"Invalid Q-id: {qid}")
        return qid

    def _ensure_pid(self, pid: str) -> str:
        """
         check P-id format.
         
         ags:
            pid: The P-id to validate (e.g., "P31").
         Returns:
            P-id.
        Raises:
            ValueError: If the P-id format is invalid.
        """
        if not _PID_RE.match(pid):
            raise ValueError(f"Invalid P-id: {pid}")
        return pid


    def build_query(self, qid: str, pid: str, year: int | None = None, language: str = "en") -> str:
        """
        Build a SPARQL query to get the value of a (statement-based) property for a given Wikidata item,
        filtered to statements whose time span overlaps a given year.

        This is useful for properties that have qualifiers like:
        - start time (P580)
        - end time (P582)

        Args:
            qid: Wikidata item id, e.g. "Q50602" (Manchester City F.C.)
            pid: Wikidata property id, e.g. "P286" (head coach)
            year: The year to filter by. If None, uses the current year (YEAR(NOW())).
            language: Label language code (default "en").

        Returns:
            A SPARQL query string.
        """
        team_qid = self._ensure_qid(qid)
        prop_pid = self._ensure_pid(pid)

        if year is not None:
            if not (1000 <= int(year) <= int(datetime.now().year)):
                self.logger.error(f"Invalid year: {year}. Expected range 1000..{int(datetime.now().year)}.")
                raise ValueError(f"Invalid year: {year}. Expected range 1000..{int(datetime.now().year)}.")

            # Fixed year range (constant) -> faster and simpler than computing in SPARQL
            year_start_expr = f'xsd:dateTime("{year}-01-01T00:00:00Z")'
            year_end_expr = f'xsd:dateTime("{year}-12-31T23:59:59Z")'
        else:
            # Dynamic current-year range computed inside SPARQL
            year_start_expr = 'xsd:dateTime(CONCAT(STR(YEAR(NOW())), "-01-01T00:00:00Z"))'
            year_end_expr = 'xsd:dateTime(CONCAT(STR(YEAR(NOW())), "-12-31T23:59:59Z"))'

        return f"""
                PREFIX wd: <http://www.wikidata.org/entity/>
                PREFIX p: <http://www.wikidata.org/prop/>
                PREFIX ps: <http://www.wikidata.org/prop/statement/>
                PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX wikibase: <http://wikiba.se/ontology#>
                PREFIX bd: <http://www.bigdata.com/rdf#>

                SELECT * WHERE {{
                wd:{team_qid} p:{prop_pid} ?st .
                ?st ps:{prop_pid} ?value .

                OPTIONAL {{ ?st pq:P580 ?start . }}  # start time
                OPTIONAL {{ ?st pq:P582 ?end . }}    # end time

                BIND({year_start_expr} AS ?yearStart)
                BIND({year_end_expr}   AS ?yearEnd)

                FILTER(!BOUND(?start) || ?start <= ?yearEnd)
                FILTER(!BOUND(?end)   || ?end   >= ?yearStart)

                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language}". }}
                }}
                ORDER BY DESC(?start)
                LIMIT 1
                """.strip()
                
    def build_get_entity_query(self, qid: str, language: str = "en") -> str:
        """
        Build a SPARQL query to get all properties and values for a given Wikidata item.

        Args:
            qid: Wikidata item id, e.g. "Q50602" (Manchester City F.C.)
        
        returns:
            A SPARQL query string.
        """
        team_qid = self._ensure_qid(qid)

        return f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX wikibase: <http://wikiba.se/ontology#>
        PREFIX bd: <http://www.bigdata.com/rdf#>

        SELECT ?property ?propertyLabel ?value ?valueLabel WHERE {{
        wd:{team_qid} ?wdtProp ?value .
        FILTER(STRSTARTS(STR(?wdtProp), STR(wdt:)))
        ?property wikibase:directClaim ?wdtProp .
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language}". }}
        }}
        ORDER BY ?property ?value
        """.strip()
            
            
    
    async def get_coach_of_team(self, team, year:int = None, language="en") -> dict | None:
        # 1) Find the team Q-id
        team_candidates = await self.search_entity(team, limit=1)
        if not team_candidates:
            self.logger.error(f"Could not find the item {team}")
            return None
        print(f'Team candidates: {[(c["id"], c.get("label"), c.get("description")) for c in team_candidates]}')
        qid = team_candidates[0]["id"] if team_candidates else None

        # 2) Find the coach property P-id
        what = "coach"
        prop_candidates = await self.search_property(what, limit=1)
        pid = prop_candidates[0]["id"] if prop_candidates else None
        if not prop_candidates:
            self.logger.error(f"Could not find the property {what}")
            return None
        print(f'Property candidates: {[(c["id"], c.get("label"), c.get("description")) for c in prop_candidates]}')

        # 3) Query WDQS
        query = self.build_query(qid=qid, pid=pid, year=year, language=language)
        data = await self.wdqs_post(query)

        bindings = data["results"]["bindings"]
        if not bindings:
            return None

        row = bindings[0]
        print(f'row: {row}')
        who_qid = row["value"]["value"].split("/")[-1]
        get_entity_query = self.build_get_entity_query(qid=who_qid, language=language)
        entity_data = await self.wdqs_post(get_entity_query)
        print(f'Entity data: {entity_data}')

        
        
    
async def main():
    client = WikidataClient(user_agent="MyWikidataClient/1.0 (contact: you@example.com)")
    result = await client.get_coach_of_team()
    
    print("Coach of Manchester City this year:", result)
        

#import asyncio            
#if __name__ == "__main__":
    #asyncio.run(main())
    