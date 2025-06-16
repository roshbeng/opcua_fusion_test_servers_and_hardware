from time import sleep
import RPi.GPIO as GPIO
import os

delay = 0.1
inPin = 6
outPin = 38

GPIO.setmode(GPIO.BCM)
GPIO.setup(outPin, GPIO.OUT)
GPIO.setup(inPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


try:
    while True:
        buttonState = GPIO.input(inPin)
        print(buttonState)
        if buttonState == 0:
            os.system("sudo shutdown -h now")
        else:
            pass
        sleep(0.1)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("GPIO good to go")