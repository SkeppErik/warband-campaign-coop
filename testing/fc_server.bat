@echo off
rem Campaign server for local tests (WSE2 dedicated campaign server, our module).
rem Continues the world in save slot 0 (sg00.sav, Documents\...\CampaignCoop\Savegames) if there is one, else
rem starts a new world. The server saves to that slot when a player leaves and once a game day.
cd /d "%~dp0"
start "CampaignCoop server" mb_warband_wse2_dedicated_campaign.exe --config-path fc_server_config.ini -r fc_server.txt --module CampaignCoop --save-no 0 --load-game
