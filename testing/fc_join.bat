@echo off
rem A game client that connects straight to the campaign server on this PC (WSE2 launch options).
rem Another PC: replace 127.0.0.1 with the server PC's address.
cd /d "%~dp0"
start "CampaignCoop join" mb_warband_wse2.exe --module CampaignCoop --no-intro --address 127.0.0.1:7240 --campaign
