import httpx
from utils.logger import Logger
from utils.wikidata_bio_fetcher import WikidataBioFetcher
import re
from datetime import datetime
import traceback

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
        self._qid = None
        self._pid = None
        self.bio_fetcher = WikidataBioFetcher(user_agent=user_agent, timeout=timeout)
        
    async def _search_(self, text: str, entity_type:str, language: str = "en", limit: int = 5) -> list[dict]:
        """
        Search on  Wikidata by text using wbsearchentities.
        Returns a list of candidates with fields like id, label, description.
        """
        try:
            params = {
                "action": "wbsearchentities",
                "format": "json",
                "search": text,
                "language": language,
                "languagefallback": 1,
                "limit": limit,
                "type": entity_type,
            }                
            async with httpx.AsyncClient(timeout=self._timeout, headers=self._headers) as client:
                r = await client.get(WIKIDATA_API, params=params)
                r.raise_for_status()
                data = r.json()
                return data.get("search", [])
        except Exception:
            self.logger.error(f"Error searching Wikidata for text '{text}': {traceback.format_exc()}")
            return []

    async def search_entity(self, entity_text: str, language: str = "en", limit: int = 1) -> bool:
        """
        Search Wikidata items (Q-ids) by text using wbsearchentities.
        
        args:
            entity_text: str - The text to search for.
            language: str - Language code for search (default "en").
            limit: int - Maximum number of results to return.
        returns:
            bool - True if an entity was found and stored, otherwise False.
        """
        team_candidates =  await self._search_(entity_text, entity_type="item", language=language, limit=limit)
        if not team_candidates:
            self.logger.warning(f"Could not find the item {entity_text}")
            return False
        #print(f'Team candidates: {[(c["id"], c.get("label"), c.get("description")) for c in team_candidates]}')
        qid = team_candidates[0]["id"] if team_candidates else None
        self._qid = qid
        return True

    async def search_property(self, property_text: str="head coach", language: str = "en", limit: int = 1) -> bool:
        """
        Search Wikidata properties (P-ids) by text using wbsearchentities.
        
        args:
            property_text: str - The text to search for.
            language: str - Language code for search (default "en").
            limit: int - Maximum number of results to return.
        returns:
            bool - True if a property was found and stored, otherwise False.
        """
        prop_candidates = await self._search_(property_text, entity_type="property", language=language, limit=limit)
        if not prop_candidates:
            self.logger.warning(f"Could not find the property {property_text}")
            return False
        #print(f'Property candidates: {[(c["id"], c.get("label"), c.get("description")) for c in prop_candidates]}')
        pid = prop_candidates[0]["id"] if prop_candidates else None
        self._pid = pid
        return True
    
    async def search_entity_and_property(self, entity_text: str, property_text: str="head coach", language: str = "en") -> bool:
        """
        Search both entity and property and store their Q-id and P-id.
        args:
            entity_text: str - The text to search for the entity.
            property_text: str - The text to search for the property.
            language: str - Language code for search (default "en").
        returns:
            bool - True if both entity and property were found, otherwise False.
        """
        do_e_exist =  await self.search_entity(entity_text, language=language)
        do_p_exist = await self.search_property(property_text, language=language)
        return do_e_exist and do_p_exist

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
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                self.logger.error(f"WDQS error: {e.response.status_code}\nQuery:\n{query}\nResponse:\n{e.response.text}")
                raise
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

                SELECT ?value ?valueLabel ?start ?end WHERE {{
                wd:{team_qid} p:{prop_pid} ?st .
                ?st ps:{prop_pid} ?value .

                OPTIONAL {{ ?st pq:P580 ?start . }}  # start time
                OPTIONAL {{ ?st pq:P582 ?end . }}    # end time

                BIND({year_start_expr} AS ?yearStart)
                BIND({year_end_expr}   AS ?yearEnd)

                FILTER(!BOUND(?start) || ?start <= ?yearEnd)
                FILTER(!BOUND(?end)   || ?end   >= ?yearStart)

                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language},en". }}
                }}
                ORDER BY DESC(?start)
                LIMIT 1
                """.strip()
    
                    
    async def get_coach_of_team(self, entity_text:str=None, property_text:str="head coach", year:int = None, language="en") -> tuple[dict, dict] | None:
        """
        Get the coach of a football team for a given year.
        Args:
            entity_text: str - The name of the football team.
            property_text: str - The property to query (default "head coach").
            year: int - The year to filter by. If None, uses the current year.
            language: str - Language code for labels (default "en").
        Returns:
            tuple[dict, dict] | None - A tuple of (entity_data, wiki_answer) if found, otherwise None.
        """
        try:
            if entity_text and property_text:
                await self.search_entity_and_property(
                    entity_text=entity_text,
                    property_text=property_text,
                    language=language
                )
            
            # 3) Query WDQS
            query = self.build_query(qid=self._qid, pid=self._pid, year=year, language=language)
            data = await self.wdqs_post(query)

            bindings = data["results"]["bindings"]
            if not bindings:
                self.logger.warning(f"No results found for team Q-id '{self._qid}' and property P-id '{self._pid}' for year '{year}'")
                return None

            row = bindings[0]
            #print(f'row: {row}')
            who_qid = row["value"]["value"].split("entity/")[-1]
            entity_data = await self.bio_fetcher.fetch_person_data_for_bio(who_qid, language=language)            
            return entity_data, row
        except Exception:
            self.logger.error(f"Error getting coach of team: {traceback.format_exc()}")
            return None

        
        
    
async def main():
    client = WikidataClient(user_agent="MyWikidataClient/1.0 (contact: jovial@test.com)")
    result = await client.get_coach_of_team("Hertha BSC", year=2021)
    
    #print("Coach of Manchester City this year:", result)
        

#import asyncio            
#if __name__ == "__main__":
    #asyncio.run(main())
    