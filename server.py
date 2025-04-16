import os, json
from flask import Flask, request, jsonify
from mcp_integration import ClaudeMCPBridge, handle_claude_tool_call


app = Flask(__name__)
bridge = ClaudeMCPBridge()
PORT = int(os.environ.get("PORT", 5001))


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "200 OK"})


@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "name": "MCP server",
        "status": "running",
        "endpoints": [
            {"path": "/health", "methods": ["GET"], "description": "Health check"},
            {"path": "/tool_call", "methods": ["POST"], "description": "Handles the Tool call"}
        ]
    })


@app.route("/tool_call", methods=["POST"])
def tool_call():
    if not request.json:
        return jsonify({"error": "Invalid request"}), 400
    
    tool_name = request.json.get("name")
    params = request.json.get("parameters", {})

    if tool_name != "fetch_web_content":
        return jsonify({"error": "Unknown Tool Name"}), 400
    
    result = handle_claude_tool_call(params)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)