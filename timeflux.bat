@echo off
REM Change to the desired directory
cd /D D:\Jules\Professionel\Stages\2024_SFE_Supaero\P2_BCI_Timeflux\timeflux_git\In-time-we-flux

REM Initialize conda
CALL conda.bat activate timeflux

REM Execute the timeflux command
timeflux -d main.yaml -E erp.env

REM Prevent the terminal from closing immediately
pause