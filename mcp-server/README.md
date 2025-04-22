## MCP Server

## Development

```sh
npx @modelcontextprotocol/inspector@latest uvx mcp-server
```

## Install

### Local

```json
"mcpServers": {
  "git": {
    "command": "uvx",
    "args": ["--from", ".", "mcp-server"]
  }
}
```

## References

- https://github.com/modelcontextprotocol/servers/tree/main/src/fetch
- https://github.com/modelcontextprotocol/servers/tree/main/src/git
- https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite
- https://github.com/modelcontextprotocol/servers/blob/a8efccb3f28d49138afeeb8676580e6d88932582/src/puppeteer/index.ts#L172
