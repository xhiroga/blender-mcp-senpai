const { spawn } = require('child_process');

// uvx --with-editable . --python 3.11 blender-mcp-senpai --development
const server = spawn('uvx', [
    '--with-editable', '.',
    '--python', '3.11',
    'blender-mcp-senpai',
    '--development'
], { stdio: ['pipe', 'pipe', 'pipe'] });


server.stdout.on('data', (data) => {
    console.log(data.toString());
});

server.stderr.on('data', (data) => {
    console.error(data.toString());
});

const initialize = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "clientInfo": {
            "name": "test.js",
            "version": "1.0.0"
        },
        "capabilities": {
            "logging": {},
            "resources": {
                "subscribe": false
            },
            "tools": {}
        }
    }
}

server.stdin.write(JSON.stringify(initialize) + '\n');
