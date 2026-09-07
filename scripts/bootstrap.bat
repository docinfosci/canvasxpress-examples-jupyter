@echo off
REM Bootstrap script for Windows - Initialize canvasxpress-examples-jupyter workspace
echo ================================================
echo  CanvasXpress Examples Jupyter - Setup
echo ================================================
echo.

REM Check for uv
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: uv not found. Please install uv first:
    echo   pip install uv
    echo   OR follow instructions at https://github.com/astral-sh/uv
    pause
    exit /b 1
)

echo [1/3] Checking Python version...
uv python install 3.12
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Python 3.12
    pause
    exit /b 1
)

echo [2/3] Installing dependencies with uv...
uv sync
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo [3/3] Installing Jupyter kernel...
uv run python -m ipykernel install --user --name canvasxpress-examples --display-name "Python 3.12 (CanvasXpress Examples)"

echo.
echo ================================================
echo  Setup Complete!
echo ================================================
echo.
echo To start JupyterLab:
echo   uv run jupyter lab
echo.
echo To start Jupyter Notebook:
echo   uv run jupyter notebook
echo.
echo Examples are in the examples/ directory
echo.
pause
