@echo off
rem Campaign server with a NEW world (ignores sg00.sav; its first save overwrites it).
cd /d "%~dp0"
start "CampaignCoop server (new world)" mb_warband_wse2_dedicated_campaign.exe --config-path fc_server_config.ini -r fc_server.txt --module CampaignCoop --save-no 0
