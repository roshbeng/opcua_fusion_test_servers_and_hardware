import asyncio
from asyncua import ua, uamethod, Server
from datetime import datetime, timezone
import re, sys, os
import RPi.GPIO as GPIO
from time import sleep

pwm_objects = {}

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

BUTTON_PIN = 6

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
async def move_arm(parent, command_bool):
    try:
        GPIO.setmode(GPIO.BCM)

        pwm16 = get_or_create_pwm(16)
        pwm25 = get_or_create_pwm(25)
        pwm23 = get_or_create_pwm(23)
        pwm24 = get_or_create_pwm(24)
        pwm26 = get_or_create_pwm(26)

        if command_bool:
            print("Moving arm...")
            pwm25.ChangeDutyCycle(8.5)
            await asyncio.sleep(1)
            pwm26.ChangeDutyCycle(12.5)
            await asyncio.sleep(1)
            pwm23.ChangeDutyCycle(3.5)
            await asyncio.sleep(1)
            pwm23.ChangeDutyCycle(6)
            await asyncio.sleep(1)
            pwm16.ChangeDutyCycle(12.5)
            await asyncio.sleep(1)
            pwm24.ChangeDutyCycle(12.5)
            await asyncio.sleep(1)
            pwm23.ChangeDutyCycle(4)
            await asyncio.sleep(1)
            pwm26.ChangeDutyCycle(10)
            await asyncio.sleep(1)
            pwm25.ChangeDutyCycle(10.5)
            await asyncio.sleep(1)
            pwm26.ChangeDutyCycle(12.5)
            await asyncio.sleep(1)
            pwm23.ChangeDutyCycle(6)
            await asyncio.sleep(1)
            pwm25.ChangeDutyCycle(9)
            await asyncio.sleep(1)
            pwm16.ChangeDutyCycle(3.5)
            await asyncio.sleep(1)
            pwm25.ChangeDutyCycle(11)
            await asyncio.sleep(1)
            pwm23.ChangeDutyCycle(4)
            await asyncio.sleep(1)
            pwm26.ChangeDutyCycle(10)
            await asyncio.sleep(1)
            pwm25.ChangeDutyCycle(9.5)
            await asyncio.sleep(1)
            pwm26.ChangeDutyCycle(12.5)
            await asyncio.sleep(1)
            pwm23.ChangeDutyCycle(3.5)
            await asyncio.sleep(1)
            print("Arm movement completed.")

            print("Going to home position...")
            pwm16.ChangeDutyCycle(7)
            await asyncio.sleep(1)
            pwm25.ChangeDutyCycle(8)
            await asyncio.sleep(1)
            pwm26.ChangeDutyCycle(10)
            await asyncio.sleep(1)
            pwm23.ChangeDutyCycle(3.5)
            await asyncio.sleep(1)
            pwm24.ChangeDutyCycle(12.5)
            await asyncio.sleep(1)
            pwm26.ChangeDutyCycle(12.5)
            await asyncio.sleep(1)
            stop_all_servos()
        else:
            print("Stopping arm movement...")

    except Exception as e:
        print(f"Error during arm movement: {e}")
        cleanup_gpio()

    return True

@uamethod
async def reference_cobot(parent):
    try:
        print("Referencing Cobot...")
        pwm16 = get_or_create_pwm(16)
        pwm25 = get_or_create_pwm(25)
        pwm23 = get_or_create_pwm(23)
        pwm24 = get_or_create_pwm(24)
        pwm26 = get_or_create_pwm(26)

        pwm16.ChangeDutyCycle(7)
        await asyncio.sleep(1)
        pwm25.ChangeDutyCycle(8)
        await asyncio.sleep(1)
        pwm26.ChangeDutyCycle(10)
        await asyncio.sleep(1)
        pwm23.ChangeDutyCycle(3.5)
        await asyncio.sleep(1)
        pwm24.ChangeDutyCycle(12.5)
        await asyncio.sleep(1)
        pwm26.ChangeDutyCycle(12.5)
        await asyncio.sleep(1)

        print("Cobot referenced successfully.")
        stop_all_servos()

    except Exception as e:
        print(f"Error during referencing: {e}")
        cleanup_gpio()

    return True

@uamethod
async def stop_cobot(parent):
    print("Cobot stopping, and shutting down the system...")
    await asyncio.sleep(3)
    stop_all_servos()
    cleanup_gpio()
    os.system("sudo shutdown -h now")
    return True


async def generate_opc_model(server, namespace_id):
    cobot_interface = await server.nodes.objects.add_object(namespace_id, "cobot interface")

    claw_position = await cobot_interface.add_variable(namespace_id, "claw position", 0.0)
    server_timestamp = await cobot_interface.add_variable(namespace_id, "server timestamp", datetime.now(timezone.utc))

    await cobot_interface.add_property(namespace_id, "Manufacturer", "HomeBuiltCobot")
    await cobot_interface.add_property(namespace_id, "Version", "1.0")

    move_functions_channel = await cobot_interface.add_object(namespace_id, "move functions channel")

    move_arm_arg = ua.Argument()
    move_arm_arg.Name = "Command"
    move_arm_arg.DataType = ua.NodeId(ua.ObjectIds.Boolean)

    method_true_output = ua.Argument()
    method_true_output.Name = "Execution Result"
    method_true_output.DataType = ua.NodeId(ua.ObjectIds.Boolean)

    await move_functions_channel.add_method(namespace_id, "move_arm", move_arm, [move_arm_arg], [method_true_output])
    await cobot_interface.add_method(namespace_id, "reference_cobot", reference_cobot, [], [method_true_output])
    await cobot_interface.add_method(namespace_id, "stop_cobot", stop_cobot, [], [method_true_output])

    return server_timestamp


async def start_server(endpoint="opc.tcp://192.168.1.3:4840/cobot_arm"):

    server = Server()
    await server.init()
    server.set_endpoint(endpoint)


    if match := re.search(r"^opc\\.tcp://(.*)/(.*)$", endpoint):
        uri = match.group(2)
    else:
        uri = "cobot_arm"

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
