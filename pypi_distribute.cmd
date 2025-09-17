@echo off
title Distribute to PyPI
SET ROOT_PATH="C:%HOMEPATH%\Desktop\Kubik\KUtil"
SET PY_PATH="C:\Python312\python.exe"

choice /c YN /m "Are you sure you want to distribute your new version AND you have updated the version in pyproject.toml?"
if %errorlevel%==1 goto yes
if %errorlevel%!=1 exit
:yes

rem WHAT'S THIS??? cd %ROOT_PATH%\package
echo Working dir: %ROOT_PATH%
rem WHAT'S THIS??? echo Package dir: %ROOT_PATH%\package
echo Python: %PY_PATH%

%PY_PATH% -m build

choice /c TP /m "Distribute to testpypi [T] or to real production pypi [P]?"
if %errorlevel%==1 goto test
if %errorlevel%==2 goto real
exit

:real
%PY_PATH%  -m twine check dist/*
%PY_PATH%  -m twine upload --repository pypi --config-file %ROOT_PATH%\.pypirc dist/*
goto end
:test
%PY_PATH%  -m twine upload --repository testpypi --config-file %ROOT_PATH%\.pypirc dist/*
goto end

:end
pause

rem https://packaging.python.org/en/latest/tutorials/packaging-projects/#generating-distribution-archives
