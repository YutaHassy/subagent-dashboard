@echo off
rem 古い版（発行元 local）の Subagent Dashboard を VSCode から抜く。
rem 0.4.3 で発行元を変えたため拡張 ID が変わった。VSCode にとっては別物の拡張なので、
rem 新しいほうを入れても古いほうは残り、2つ並んで動いてしまう。
rem このファイルは自動生成物（build_vsix.py の CLEANUP_TEMPLATE）。手で直さないこと。

rem 遅延展開は使わない。有効にすると案内文の [!] の ! が消える。
setlocal
for /f "tokens=2 delims=:" %%c in ('chcp') do set "SAVED_CP=%%c"
chcp 932 >nul

set "OLD_IDS=local.agent-dashboard"

echo.
echo   古い版の Subagent Dashboard を抜きます
echo   ================================================
echo.

set "CODE="
for /f "delims=" %%p in ('where code 2^>nul') do if not defined CODE set "CODE=%%p"
if not defined CODE if exist "%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd" set "CODE=%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"
if not defined CODE if exist "%ProgramFiles%\Microsoft VS Code\bin\code.cmd" set "CODE=%ProgramFiles%\Microsoft VS Code\bin\code.cmd"

if not defined CODE (
  echo   [!] VSCode の code コマンドが見つかりませんでした。
  echo.
  echo       お手数ですが、手で抜いてください。
  echo         1. VSCode を開く
  echo         2. Ctrl+Shift+X で拡張機能パネルを開く
  echo         3. 「Subagent Dashboard」で検索する
  echo            出てこないときは、検索欄に @installed agent-dashboard と入れる
  echo         4. 発行元が local のほうを右クリックし、アンインストールを選ぶ
  goto :done
)

echo   VSCode        %CODE%
echo.

set /a REMOVED=0
set /a FAILED=0
for %%i in (%OLD_IDS%) do (
  call "%CODE%" --list-extensions | findstr /i /x /c:"%%i" >nul
  if errorlevel 1 (
    echo   入っていません: %%i
  ) else (
    echo   抜いています: %%i
    call "%CODE%" --uninstall-extension %%i
    if errorlevel 1 (set /a FAILED+=1) else (set /a REMOVED+=1)
  )
)

echo.
if %FAILED% GTR 0 (
  echo   [!] 抜けなかったものがあります。
  echo       VSCode を閉じてからもう一度実行するか、拡張機能パネル（Ctrl+Shift+X）で
  echo       「Subagent Dashboard」または @installed agent-dashboard で探し、
  echo       発行元が local のほうを手で削除してください。
) else if %REMOVED% GTR 0 (
  echo   [OK] 抜きました。VSCode を開いているときは再読み込みしてください。
  echo        Ctrl+Shift+P → Reload Window
) else (
  echo   [OK] 古い版は入っていませんでした。何もしていません。
)

echo.
echo   作業の記録（.claude\agent-dashboard）には触っていません。
echo   新しい版を入れると、そのまま続きから見られます。

:done
echo.
pause
chcp %SAVED_CP% >nul
endlocal
