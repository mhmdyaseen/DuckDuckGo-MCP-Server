import os, re, json, requests
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass, asdict
import openai, anthropic


CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
DUCKDUCKGO_ENDPOINT = "https://api.duckduckgo.com"
LLMProvider = Literal["claude"]


@dataclass
class Request:
    q: str
    format: str = "json"
    no_html: int = 1
    skip_disambig: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    

@dataclass
class Result:
    title: str
    url: str
    description: str


class MCPClient:
    def __init__(self, endpoint: str = DUCKDUCKGO_ENDPOINT):
        self.endpoint = endpoint


    def search(self, query: str, count: int = 10) -> List[Result]:
        request = Request(q=query)

        try:
            response = requests.get(
                self.endpoint,
                params=request.to_dict()
            )

            response.raise_for_status()

            data = response.json()
            results = []

            if data.get("Abstract"):
                results.append(Result(
                    title=data.get("Heading", ""),
                    url = data.get("AbstractURL", ""),
                    description=data.get("Abstract", "")
                ))
            return results
        except Exception as e:
            print(e)
            return []
    

class ClaudeMCPBridge:
    def __init__(self, llm_provider: LLMProvider = "claude"):
        self.mcp_client = MCPClient()
        self.llm_provider = llm_provider

        if llm_provider == "claude":
            self.claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


    def extract_website_queries_with_llm(self, user_message: str) -> List[str]:
        if self.llm_provider == "claude":
            return self._extract_with_claude(user_message)
        else:
            return ["error"]


    def _extract_with_claude(self, user_message: str) -> List[str]:

        try:
            response = self.claude_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0.1,
                system="Hey Claude, Extract any specific website topic queries the user wants know about. Return it's results as JSON object with a 'queries' field containing an array of strings. If no queries are found, return an empty array.",
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            content = response.content[0].text
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
            if json_match:
                result= json.loads(json_match.group(1))
            else:
                try:
                    result = json.loads(content)

                except:
                    return "error"
            queries = result.get("queries", [])
            return queries
        
        except Exception as e:
            print(e)
            return []
        

def handle_claude_tool_call(tool_params: Dict[str, Any]) -> Dict[str, Any]:
    query = tool_params.get("query", "")
    if not query:
        return {"error": "no query"}
    
    bridge = ClaudeMCPBridge()
    results = bridge.mcp_client.search(query)

    return {
        "results": [asdict(result) for result in results]
    }
    

        
    