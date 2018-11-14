
SET outputFilename=181113_CPMG_5

REM ==================
REM Acquisition
REM ==================
SET nPoints=2048
SET nScans=20
SET nEchoes=8
SET SW_kHz=513.283
REM ==================
REM Excitation
REM ==================
SET carrierFreq_MHz=14.46
SET amplitude=1.0
SET p90Time_us=1.0
REM ==================
REM Delays
REM ==================
SET transTime_us=10.0
SET tauDelay_us=4000.0
SET repetitionDelay_s=1.0

SET tx_phase=0.0

SET adcOffset=43

COPY CPMG.bat %outputFilename%_params.txt

REM Specify C program then call variables
CPMG %nPoints% %nScans% %nEchoes% %SW_kHz% %carrierFreq_MHz% %amplitude% %p90Time_us% %transTime_us% %tauDelay_us% %repetitionDelay_s% %tx_phase% %adcOffset% %outputFilename%
