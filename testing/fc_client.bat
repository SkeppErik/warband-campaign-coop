@echo off
rem A game client with our module. Join from Multiplayer: the WSE2 "Join campaign" button, address 127.0.0.1:7240.
cd /d "%~dp0"
start "CampaignCoop client" mb_warband_wse2.exe --module CampaignCoop --no-intro
