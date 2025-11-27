@echo off
echo Start time: %time%
arduino-cli compile --fqbn esp32:esp32:nodemcu-32s --libraries C:\Users\User\Documents\Arduino\libraries servo.ino
arduino-cli upload -p COM4 --fqbn esp32:esp32:nodemcu-32s:UploadSpeed=921600 .\servo.ino
echo End time: %time%
pause