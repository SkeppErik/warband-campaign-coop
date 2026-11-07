@echo off
rem Campaign server for local tests (WSE2 dedicated campaign server, our module).
cd /d "%~dp0"
start "CampaignCoop server" mb_warband_wse2_dedicated_campaign.exe --config-path server_config.ini -r fc_server.txt --module CampaignCoop
