import RPi.GPIO as GPIO
from time import sleep
                                                              
GPIO.setmode(GPIO.BCM)
pwmPin16 = 16
GPIO.setup(pwmPin16, GPIO.OUT)
pwm16=GPIO.PWM(pwmPin16,50)
pwm16.start(0)

pwmPin25 = 25
GPIO.setup(pwmPin25, GPIO.OUT)
pwm25=GPIO.PWM(pwmPin25,50)
pwm25.start(0)

pwmPin23 = 23
GPIO.setup(pwmPin23, GPIO.OUT)
pwm23=GPIO.PWM(pwmPin23,50)
pwm23.start(0)

pwmPin24 = 24
GPIO.setup(pwmPin24, GPIO.OUT)
pwm24=GPIO.PWM(pwmPin24,50)
pwm24.start(0)

pwmPin26 = 26
GPIO.setup(pwmPin26, GPIO.OUT)
pwm26=GPIO.PWM(pwmPin26,50)
pwm26.start(0)


try:
    pwm25.ChangeDutyCycle(float(8.5))
    sleep(1)
    pwm26.ChangeDutyCycle(float(12.5))
    sleep(1)
    pwm23.ChangeDutyCycle(float(3.5))
    sleep(1)
    pwm23.ChangeDutyCycle(float(6))
    sleep(1)

    pwm16.ChangeDutyCycle(float(12.5))
    sleep(1)
    pwm24.ChangeDutyCycle(float(12.5))
    sleep(1)
    pwm23.ChangeDutyCycle(float(4))
    sleep(1)
    pwm26.ChangeDutyCycle(float(10))
    sleep(1)
    pwm25.ChangeDutyCycle(float(10.6))
    sleep(1)
    pwm26.ChangeDutyCycle(float(12.5))
    sleep(1)
    pwm23.ChangeDutyCycle(float(6))
    sleep(1)
    pwm25.ChangeDutyCycle(float(9))
    sleep(1)
    pwm16.ChangeDutyCycle(float(3.5))
    sleep(1)
    pwm25.ChangeDutyCycle(float(11))
    sleep(1)
    pwm23.ChangeDutyCycle(float(4))
    sleep(1)
    pwm26.ChangeDutyCycle(float(10))
    sleep(1)
    pwm25.ChangeDutyCycle(float(8.5))
    sleep(1)
    pwm26.ChangeDutyCycle(float(12.5))
    sleep(1)
    pwm23.ChangeDutyCycle(float(3.5))
    sleep(1)


    GPIO.cleanup()
except KeyboardInterrupt:
    GPIO.cleanup()