# run from directory containing your scripts to compile
# $ ./../compile_swig.sh
echo "about to compile..."
winpty ./../swig.exe -python -o Hahn_echo_wrap.c Hahn_echo.i
gcc -shared -DMS_WIN64 -I'C:\ProgramData\Anaconda2\include' -I'C:\apps-su\spincore_apps' -L'C:\ProgramData\Anaconda2\libs' -L'C:\apps-su\spincore_apps' Hahn_echo.c Hahn_echo_wrap.c -lpython27 -lmrispinapi64 -o _Hahn_echo.pyd
echo "compiled."
