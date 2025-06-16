import tkinter as tk
import threading
import asyncio
import datetime
import re
from asyncua import ua, uamethod, Server
from datetime import datetime, timezone

class OPCUAServer:
    def __init__(self, endpoint, uri, update_variable_callback, log_method_callback):
        self.endpoint = endpoint
        self.uri = uri
        self.update_variable = update_variable_callback
        self.log_method = log_method_callback
        self.server_running = True
        self.loop = None

        self.prev_x = 0.0
        self.prev_z = 0.0
        self.prev_time = datetime.now(timezone.utc)
        self.g_code_func_running = False

    async def start_server(self):
        self.loop = asyncio.get_running_loop()
        server = Server()
        await server.init()
        server.set_endpoint(self.endpoint)
        namespace_id = await server.register_namespace(self.uri)
        await self.generate_opc_model(server, namespace_id)

        async with server:
            print(f"OPC UA Server started at {self.endpoint}")
            while self.server_running:
                if not self.g_code_func_running:
                    current_time = datetime.now(timezone.utc)
                    await self.mydtvar.write_value(current_time)
                    self.update_variable("server_timestamp", current_time)
                await asyncio.sleep(0.5)
            print("Server stopping...")

    def stop(self):
        self.server_running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

    async def generate_opc_model(self, server, namespace_id):
        cnc_interface = await server.nodes.objects.add_object(namespace_id, "cnc interface")

        cnc_axis_list = await cnc_interface.add_object(namespace_id, "cnc axis list")

        x_axis = await cnc_axis_list.add_object(namespace_id, "x axis")
        self.x_position_direct = await x_axis.add_variable(namespace_id, "x position direct", 0.0)
        self.x_velocity = await x_axis.add_variable(namespace_id, "x velocity", 0.0)
        self.x_acceleration = await x_axis.add_variable(namespace_id, "x acceleration", 0.0)

        z_axis = await cnc_axis_list.add_object(namespace_id, "z axis")
        self.z_position_direct = await z_axis.add_variable(namespace_id, "z position direct", 0.0)
        self.z_velocity = await z_axis.add_variable(namespace_id, "z velocity", 0.0)
        self.z_acceleration = await z_axis.add_variable(namespace_id, "z acceleration", 0.0)

        cnc_spindle_list = await cnc_interface.add_object(namespace_id, "cnc spindle list")
        spindle = await cnc_spindle_list.add_object(namespace_id, "spindle")
        self.spindle_speed_direct = await spindle.add_variable(namespace_id, "spindle speed direct", 0.0)

        cnc_channel_list = await cnc_interface.add_object(namespace_id, "cnc channel list")
        feed_rate_channel = await cnc_channel_list.add_object(namespace_id, "feed rate channel")
        self.feed_rate_direct = await feed_rate_channel.add_variable(namespace_id, "feed rate direct", 0.0)

        timestamp_channel = await cnc_channel_list.add_object(namespace_id, "timestamp channel")
        self.mydtvar = await timestamp_channel.add_variable(namespace_id, "server timestamp", datetime.now(timezone.utc))

        g_functions_channel = await cnc_channel_list.add_object(namespace_id, "g function channel")

        run_gcode_arg = ua.Argument()
        run_gcode_arg.Name = "G-Code Command"
        run_gcode_arg.DataType = ua.NodeId(ua.ObjectIds.String)

        method_true_output = ua.Argument()
        method_true_output.Name = "Execution Result"
        method_true_output.DataType = ua.NodeId(ua.ObjectIds.Boolean)

        await g_functions_channel.add_method(namespace_id, "run_g_code", self.run_gcode, [run_gcode_arg], [method_true_output])

        await cnc_channel_list.add_method(namespace_id, "reference_cnc_machine", self.reference_cnc, [], [method_true_output])
        await cnc_channel_list.add_method(namespace_id, "stop_cnc_machine", self.stop_cnc_machine, [], [method_true_output])

    @uamethod
    async def run_gcode(self, parent, gcode_str):
        self.log_method("run_gcode", f"Method called with argument: {gcode_str}")
        if not isinstance(gcode_str, str):
            print("G-code must be a string.")
            self.log_method("run_gcode", "G-code must be a string.")
            return False

        lines = gcode_str.strip().split('\n')

        self.g_code_func_running = True

        for line in lines:
            line = line.strip()
            if not line or line.startswith('(') or line.startswith('%'):
                continue

            match = re.match(r'(G0[01])\s*(X([-+]?[0-9]*\.?[0-9]+))?\s*(Z([-+]?[0-9]*\.?[0-9]+))?', line)
            if match:
                g_command = match.group(1)
                x_value = match.group(3)
                z_value = match.group(5)

                current_time = datetime.now(timezone.utc)
                delta_time = (current_time - self.prev_time).total_seconds()
                if delta_time == 0:
                    delta_time = 0.001

                if x_value is not None:
                    x_value = float(x_value)
                    x_vel = (x_value - self.prev_x) / delta_time
                    x_acc = (x_vel - await self.x_velocity.read_value()) / delta_time if delta_time > 0 else 0
                    await self.x_position_direct.write_value(x_value)
                    await self.x_velocity.write_value(x_vel)
                    await self.x_acceleration.write_value(x_acc)
                    self.update_variable("x_position_direct", x_value)
                    self.update_variable("x_velocity", x_vel)
                    self.update_variable("x_acceleration", x_acc)
                    self.prev_x = x_value

                if z_value is not None:
                    z_value = float(z_value)
                    z_vel = (z_value - self.prev_z) / delta_time
                    z_acc = (z_vel - await self.z_velocity.read_value()) / delta_time if delta_time > 0 else 0
                    await self.z_position_direct.write_value(z_value)
                    await self.z_velocity.write_value(z_vel)
                    await self.z_acceleration.write_value(z_acc)
                    self.update_variable("z_position_direct", z_value)
                    self.update_variable("z_velocity", z_vel)
                    self.update_variable("z_acceleration", z_acc)
                    self.prev_z = z_value

                await self.mydtvar.write_value(current_time)
                self.update_variable("server_timestamp", current_time)
                self.prev_time = current_time

            spindle_match = re.search(r'S([-+]?[0-9]*\.?[0-9]+)', line, re.IGNORECASE)
            if spindle_match:
                spindle_speed = float(spindle_match.group(1))
                await self.spindle_speed_direct.write_value(spindle_speed)
                self.update_variable("spindle_speed_direct", spindle_speed)

            feedrate_match = re.search(r'F([-+]?[0-9]*\.?[0-9]+)', line, re.IGNORECASE)
            if feedrate_match:
                feed_rate = float(feedrate_match.group(1))
                await self.feed_rate_direct.write_value(feed_rate)
                self.update_variable("feed_rate_direct", feed_rate)

            await asyncio.sleep(0.5)

        print("G-code execution completed.")
        self.log_method("run_gcode", "Method executed successfully.")
        self.g_code_func_running = False
        return True

    @uamethod
    async def reference_cnc(self, parent):
        self.log_method("reference_cnc", "Method called")
        print("Starting CNC referencing...")

        await self.x_position_direct.write_value(0.0)
        await self.z_position_direct.write_value(0.0)
        self.update_variable("x_position_direct", 0.0)
        self.update_variable("z_position_direct", 0.0)
        await asyncio.sleep(3)

        print("CNC referencing completed.")
        self.log_method("reference_cnc", "Method executed successfully.")
        return True

    @uamethod
    async def stop_cnc_machine(self, parent):
        self.log_method("stop_cnc_machine", "Method called")
        print("CNC stopped....")
        self.log_method("stop_cnc_machine", "Method executed successfully.")
        return True

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OPC UA Server Interface")


        bold_font = ('Arial', 12, 'bold')
        entry_font = ('Arial', 10)

        self.endpoint_label = tk.Label(self, text="Endpoint:", font=bold_font)
        self.endpoint_label.pack(pady=(10, 0))
        self.endpoint_entry = tk.Entry(self, width=50, font=entry_font)
        self.endpoint_entry.pack(pady=(0, 10))
        self.endpoint_entry.insert(0, "opc.tcp://localhost:4840/cnc_concept_turn_155_one")

        self.uri_label = tk.Label(self, text="URI:", font=bold_font)
        self.uri_label.pack(pady=(0, 0))
        self.uri_entry = tk.Entry(self, width=50, font=entry_font)
        self.uri_entry.pack(pady=(0, 20))
        self.uri_entry.insert(0, "cnc_concept_turn_155_one")
        self.default_fg_color = self.endpoint_entry.cget('fg')


        self.start_button = tk.Button(self, text="Start Server", command=self.start_server, font=bold_font)
        self.start_button.pack(pady=(0, 5))
        self.stop_button = tk.Button(self, text="Stop Server", command=self.stop_server, font=bold_font)
        self.stop_button.pack(pady=(0, 30))


        self.variables_frame = tk.Frame(self)
        self.variables_frame.pack(pady=(0, 10))
        self.variables_label = tk.Label(self.variables_frame, text="Realtime Variables", font=bold_font)
        self.variables_label.pack(pady=(0, 10))


        self.variable_labels = {}
        variable_names = [
            "x_position_direct", "x_velocity", "x_acceleration",
            "z_position_direct", "z_velocity", "z_acceleration",
            "spindle_speed_direct", "feed_rate_direct", "server_timestamp"
        ]
        for var_name in variable_names:
            label = tk.Label(self.variables_frame, text=f"{var_name}: N/A", font=entry_font)
            label.pack(pady=2)
            self.variable_labels[var_name] = label


        self.variable_labels["server_timestamp"].pack_configure(pady=(2, 10))


        self.methods_frame = tk.Frame(self)
        self.methods_frame.pack(pady=(0, 10))
        self.methods_label = tk.Label(self.methods_frame, text="UA Methods Execution", font=bold_font)
        self.methods_label.pack(pady=(0, 5))

        self.method_container = tk.Frame(self.methods_frame)
        self.method_container.pack()


        self.method_frames = {}
        method_names = ["run_gcode", "reference_cnc", "stop_cnc_machine"]
        for i, method_name in enumerate(method_names):
            frame = tk.Frame(self.method_container, borderwidth=2, relief="groove")
            frame.grid(row=0, column=i, padx=5, pady=5)

            label = tk.Label(frame, text=method_name, font=bold_font)
            label.pack(pady=(5, 5))

            text = tk.Text(frame, height=5, width=30, font=entry_font)
            text.pack()

            self.method_frames[method_name] = text

        self.server_thread = None
        self.server_running = False
        self.shared_data = {}
        self.loop = None


        self.update_ui()

    def start_server(self):
        if not self.server_running:
            endpoint = self.endpoint_entry.get()
            uri = self.uri_entry.get()
            self.server_running = True
            self.opcua_server = OPCUAServer(endpoint, uri, self.update_variable, self.log_method_execution)
            self.server_thread = threading.Thread(target=self.run_server_thread, daemon=True)
            self.server_thread.start()
            print("Server thread started.")
            self.endpoint_entry.config(fg='green')
            self.uri_entry.config(fg='green')

    def stop_server(self):
        if self.server_running:
            self.server_running = False
            self.opcua_server.stop()
            print("Server stopping...")
            self.endpoint_entry.config(fg=self.default_fg_color)
            self.uri_entry.config(fg=self.default_fg_color)

    def run_server_thread(self):
        asyncio.run(self.opcua_server.start_server())

    def update_variable(self, var_name, value):
        self.shared_data[var_name] = value

    def log_method_execution(self, method_name, message):
        def append_log():
            text_widget = self.method_frames.get(method_name)
            if text_widget:
                text_widget.insert(tk.END, message + "\n")
                text_widget.see(tk.END)
        self.after(0, append_log)

    def update_ui(self):
        for var_name, label in self.variable_labels.items():
            value = self.shared_data.get(var_name, "N/A")
            if isinstance(value, datetime):
                value = value.strftime("%Y-%m-%d %H:%M:%S")
            label.config(text=f"{var_name}: {value}")
        self.after(500, self.update_ui)

if __name__ == "__main__":
    app = Application()
    app.mainloop()
