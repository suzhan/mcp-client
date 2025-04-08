
# MCP Client for Server Debugging

A comprehensive debugging tool for Model Context Protocol (MCP) servers, built with Python 3.12 and Vue.

![MCP Client](https://img.shields.io/badge/MCP-Client-blue)
![Python](https://img.shields.io/badge/Python-3.12-green)
![Vue](https://img.shields.io/badge/Vue-3-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Overview

This MCP Client provides a user-friendly interface for debugging and testing MCP servers. It leverages the Model Context Protocol Python SDK to establish connections, execute tools, access resources, and utilize prompts exposed by MCP servers.

## Key Features

- 🔌 Connect to multiple MCP servers simultaneously
- 🛠️ Discover and execute tools with proper parameter validation
- 📂 Browse and access resources exposed by servers
- 📝 Test prompts with custom arguments
- 📊 View server responses in formatted outputs
- 🔄 Monitor real-time server events and notifications
- 📱 Responsive UI for both desktop and mobile use

## Installation

### Prerequisites

- Python 3.12 or higher
- Node.js 16 or higher
- npm 8 or higher

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/suzhan/mcp-client.git
   cd mcp-client
   ```

2. Set up the backend:
   ```bash
   cd mcp_backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up the frontend:
   ```bash
   cd ../mcp_frontend
   npm install
   ```

4. Create configuration directory:
   ```bash
   mkdir -p .config
   ```

5. Create configuration files:
   - Create `.config/llm.json` with your LLM provider details
   - Create `.config/servers.json` with your MCP server configurations

## Configuration

### LLM Configuration

Create a `.config/llm.json` file in the root directory with your LLM provider details:

```json
{
  "providers": [
    {
      "name": "OpenAI",
      "api_key": "your-openai-api-key",
      "models": ["gpt-3.5-turbo", "gpt-4"]
    },
    {
      "name": "Anthropic",
      "api_key": "your-anthropic-api-key",
      "models": ["claude-2", "claude-instant-1"]
    }
  ],
  "default_provider": "OpenAI",
  "default_model": "gpt-3.5-turbo"
}
```

### Server Configuration

Create a `.config/servers.json` file in the root directory with your MCP server configurations:

```json
{
  "servers": [
    {
      "name": "Local File Server",
      "type": "stdio",
      "command": "python",
      "args": ["path/to/file_server.py"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "Remote API Server",
      "type": "sse",
      "url": "https://example.com/mcp/sse",
      "headers": {
        "Authorization": "Bearer your-api-key"
      }
    }
  ]
}
```

## Usage

### Starting the Backend

```bash
cd mcp_backend
python run.py
```

The backend API will be available at `http://localhost:8000`.

### Starting the Frontend

```bash
cd mcp_frontend
npm run dev
```

The frontend will be available at `http://localhost:5173` (or the port shown in your terminal).

## Features and Workflows

### Connecting to Servers

1. Navigate to the Servers tab
2. Select a server from your configuration
3. Click "Connect" to establish the connection
4. View connection status and server capabilities

### Discovering and Executing Tools

1. Navigate to the Tools tab
2. Browse available tools from connected servers
3. Select a tool to view its parameters and description
4. Enter parameter values and execute the tool
5. View formatted results

### Browsing Resources

1. Navigate to the Resources tab
2. Browse available resources from connected servers
3. Click on a resource to view its contents
4. Subscribe to resource updates when available

### Testing Prompts

1. Navigate to the Prompts tab
2. Select a prompt from available templates
3. Fill in arguments required by the prompt
4. View the generated prompt messages
5. Send to LLM if desired

## API Documentation

The backend exposes several REST endpoints for managing MCP connections:

- `GET /api/servers`: List configured servers
- `POST /api/servers/connect`: Connect to a server
- `GET /api/servers/{server_id}/tools`: List tools for a connected server
- `POST /api/servers/{server_id}/tools/{tool_name}`: Execute a tool
- `GET /api/servers/{server_id}/resources`: List resources for a server
- `GET /api/servers/{server_id}/resources/{resource_uri}`: Read a resource
- `GET /api/servers/{server_id}/prompts`: List prompts for a server
- `POST /api/servers/{server_id}/prompts/{prompt_name}`: Get a prompt with arguments

## Architecture

This project follows a standard client-server architecture:

- **Backend**: Python FastAPI application that manages MCP connections
- **Frontend**: Vue.js application with Composition API and TypeScript
- **Communication**: JSON-RPC 2.0 over HTTP/WebSockets

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Vue.js Framework: https://vuejs.org
- FastAPI: https://fastapi.tiangolo.com


## screenshot

### MCP Server Management
![screenshot-1](hhttps://github.com/suzhan/mcp-client/docs/mcp-client-1.jpg)

### LLM Provider Management
![screenshot-2](hhttps://github.com/suzhan/mcp-client/docs/mcp-client-2.jpg)

### Chat
![screenshot-3](hhttps://github.com/suzhan/mcp-client/docs/mcp-client-3.jpg)
