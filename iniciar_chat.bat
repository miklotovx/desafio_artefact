@echo off
rem Starts the local Streamlit chat in the default browser.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado. Siga as instrucoes do README.md.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run app.py --server.address localhost --server.headless false
if errorlevel 1 (
    echo Nao foi possivel iniciar o chat. Confira a mensagem acima.
    pause
    exit /b 1
)
endlocal
