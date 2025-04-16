import os, json, requests, time
from typing import Dict, List, Any, Optional


CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:5001")


class ClaudeClient:
    def __init__(self, api_key: str = CLAUDE_API_KEY, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key
        self.model = model
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        self.tools = [{
            "name": "fetch_web_content",
            "description": "Extracts info from websites based on user\'s queries",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up info about"
                    }
                },
                "required": ["query"]
            }
        }]

        self._check_mcp_server()


    def _check_mcp_server(self):
        try:
            response = requests.get(f"{MCP_SERVER_URL}/health", timeout=3)
            if response.status_code == 200:
                return True
        except:
            pass
        return False
    

    def send_message(self, message: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("API key not set")
        
        if conversation_history is None:
            conversation_history = []

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": conversation_history + [{"role": "user", "content": message}],
            "tools": self.tools
        }

        print("Sending Request to Claude...")

        try:
            response = requests.post(
                CLAUDE_API_URL,
                headers=self.headers,
                json=payload
            )

            if response.status_code != 200:
                print(response.json)
                raise ValueError("Error")

            response.raise_for_status()

            result = response.json()
            print(f"Claude Response: {result}")

            has_tool_call = False
            tool_call = {}
            if "content" in result:
                for content_block in result.get("content", []):
                    if content_block.get("type") == "tool_use":
                        has_tool_call = True
                        print("Tool call detected")
                        tool_call["name"] = content_block.get("name", "")
                        tool_call["parameters"] = {}
                        tool_call["parameters"]["query"] = content_block.get("input", {}).get("query", {})
                        print(f"Tool call details: {tool_call}")

                        tool_response = self._handle_tool_call(tool_call)
                        print(f"tool response: {tool_response}")

                        conversation_history.append({"role": "user", "content": message})
                        conversation_history.append({"role": "assistant", "content": [
                            {"type": "text", "text": result.get("content", [{}])[0].get("text", "") + "\n\nThe tool call was successful and here is the information from the tool call: " + tool_response["results"][0]["description"]}
                        ]})

                        return self.send_message("Please Summarize the information from the tool call and don\'t forget to include the source of the information", conversation_history)
        
            if not has_tool_call:
                print("No Tool call detected")

            return result
        
        except Exception as e:
            print(e)


    def _handle_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = tool_call.get("name")
        tool_params = tool_call.get("parameters")

        if not self._check_mcp_server():
            return {
                "error": "MCP server not there"
            }
        
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = requests.post(
                    f"{MCP_SERVER_URL}/tool_call",
                    json={"name": tool_name, "parameters": tool_params},
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
            
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2**retry_count
                    time.sleep(wait_time)
                else:
                    return {
                        "error": "MCP Server not Responding"
                    }
                

    def get_final_answer(self, message: str) -> str:
        try:
            response = self.send_message(message)

            if "content" in response:
                for content_block in response.get("content", []):
                    if content_block.get("type") == "text":
                        return content_block.get("text", "")
            return "No clear answer found"
        
        except Exception as e:
            return f"Error: {e}"