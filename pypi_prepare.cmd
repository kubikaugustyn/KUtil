@echo off
title Prepare PyPI upload
SET ROOT_PATH="C:%HOMEPATH%\Desktop\Kubik\KUtil"

cd %ROOT_PATH%
echo Working dir: %ROOT_PATH%

rem Clear previous run
echo Delete current package dir: %ROOT_PATH%\package
rmdir %ROOT_PATH%\package /s
mkdir %ROOT_PATH%\package

rem Create dirs
mkdir %ROOT_PATH%\package\src

rem Link source code
mklink /d %ROOT_PATH%\package\src\kutil %ROOT_PATH%\kutil
rem Link test code
mklink /d %ROOT_PATH%\package\tests %ROOT_PATH%\tests
rem Link .git for version or whatever
mklink /d %ROOT_PATH%\package\.git %ROOT_PATH%\.git

rem Link additional files
mklink %ROOT_PATH%\package\LICENSE %ROOT_PATH%\LICENSE
mklink %ROOT_PATH%\package\pyproject.toml %ROOT_PATH%\pyproject.toml
mklink %ROOT_PATH%\package\README.md %ROOT_PATH%\README.md
mklink %ROOT_PATH%\package\requirements.txt %ROOT_PATH%\requirements.txt

pause

rem https://packaging.python.org/en/latest/tutorials/packaging-projects/#creating-the-package-files
