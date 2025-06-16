import asyncio
from asyncua import ua, uamethod, Server
from datetime import datetime, timezone
import re, sys, os
import RPi.GPIO as GPIO


pwm_objects = {}


SERVO_PIN = 18
BUTTON_PIN = 6

def get_or_create_pwm(pin, frequency=50):

    if pin not in pwm_objects:
        GPIO.setup(pin, GPIO.OUT)
        new_pwm = GPIO.PWM(pin, frequency)
        new_pwm.start(0)
        pwm_objects[pin] = new_pwm
    return pwm_objects[pin]

def stop_all_servos():

    for pwm_obj in pwm_objects.values():
        pwm_obj.stop()
    pwm_objects.clear()

def cleanup_gpio():

    GPIO.cleanup()
    print("GPIO cleanup completed.")

async def monitor_button():

    while True:
        button_state = GPIO.input(BUTTON_PIN)
        if button_state == 0:
            print("Physical button pressed - shutting down system...")
            stop_all_servos()
            cleanup_gpio()
            os.system("sudo shutdown -h now")
        await asyncio.sleep(0.1)

@uamethod
async def initialize(parent):

    try:
        GPIO.setmode(GPIO.BCM)
        servo_pwm = get_or_create_pwm(SERVO_PIN)
        print("Initializing conveyor...")
        servo_pwm.ChangeDutyCycle(12.5)
        await asyncio.sleep(1)
        stop_all_servos()
        print("Conveyor initialized.")
    except Exception as e:
        print(f"Error during initialization: {e}")
        cleanup_gpio()
    return True

@uamethod
async def move_and_supply(parent):

    try:
        GPIO.setmode(GPIO.BCM)
        servo_pwm = get_or_create_pwm(SERVO_PIN)
        print("Moving conveyor and supplying items...")
        servo_pwm.ChangeDutyCycle(3)
        await asyncio.sleep(1)
        stop_all_servos()
        print("Conveyor movement and supply completed.")
    except Exception as e:
        print(f"Error during move and supply: {e}")
        cleanup_gpio()
    return True

async def generate_opc_model(server, namespace_id):

    conveyor_interface = await server.nodes.objects.add_object(namespace_id, "conveyor interface")

    server_timestamp = await conveyor_interface.add_variable(namespace_id, "server timestamp", datetime.now(timezone.utc))
    await conveyor_interface.add_property(namespace_id, "Manufacturer", "HomeBuiltConveyor")
    await conveyor_interface.add_property(namespace_id, "Version", "1.0")

    await conveyor_interface.add_method(namespace_id, "initialize", initialize, [], [ua.Argument(Name="Execution Result", DataType=ua.NodeId(ua.ObjectIds.Boolean))])
    await conveyor_interface.add_method(namespace_id, "move_and_supply", move_and_supply, [], [ua.Argument(Name="Execution Result", DataType=ua.NodeId(ua.ObjectIds.Boolean))])

    return server_timestamp

async def start_server(endpoint="opc.tcp://192.168.1.2:4840/conveyor"):

    server = Server()
    await server.init()
    server.set_endpoint(endpoint)

    if match := re.search(r"^opc\\.tcp://(.*)/(.*)$", endpoint):
        uri = match.group(2)
    else:
        uri = "conveyor"

    namespace_id = await server.register_namespace(uri)
    server_timestamp = await generate_opc_model(server, namespace_id)


    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    async with server:
        print(f"OPC UA Server started at {endpoint}")


        asyncio.create_task(monitor_button())


        while True:
            await server_timestamp.write_value(datetime.now(timezone.utc))
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        GPIO.setmode(GPIO.BCM)
        asyncio.run(start_server())
    except (KeyboardInterrupt, SystemExit):
        cleanup_gpio()
        sys.exit(0)
