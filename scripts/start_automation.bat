@echo off
echo Starting AI Automation Endpoint...
python -c "from integrations.endpoint_server import start_server; start_server()"
pause
