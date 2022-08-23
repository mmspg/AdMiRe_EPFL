import json
import http.server
import socket
import os
import psutil
import time

from subprocess import Popen

HOST = ''
PORT = 9000

IS_SHOW = False
IS_VERBOSE = True

#MAXINE_EXE_PATH = f'C:/Users/\"{os.getlogin()}\"/MAXINE-VFX-SDK-master-OSS/build/Release'
MAXINE_EXE_PATH = 'C:/\"Program Files\"/MMSPG_EPFL/admire_effects'
EXE_NAMES = ["AigsEffectApp", "VideoEffectsApp"]

MODNet_BE_PYTHON_SCRIPT_PATH = f'C:/Users/\"{os.getlogin()}\"/Documents/AdMiRe/src/be_sr_modules/MODNet/run.py'
RVM_BE_PYTHON_SCRIPT_PATH = f'C:/Users/\"{os.getlogin()}\"/Documents/AdMiRe/src/be_sr_modules/robust_video_matting/run.py'

BE_MODULE_NAMES = ["NVIDIA_MAXINE", "MODNet", "RVM"]

P_LIST = []

# Function checking that the request is in a json format
def is_json_request(request):
    try:
        json.loads(request)
    except ValueError as e:
        return False
    return True


def check_process_list(p_list):
    global P_LIST
    msg_list = []
    new_p_list = []

    for pid, p_name in p_list:
        is_alive = psutil.pid_exists(pid)
        if is_alive:
            msg_list.append(f'{p_name} is ON (PARENT_PID={pid}).')
            new_p_list.append((pid, p_name))
        else:
            msg_list.append(f'{p_name} is OFF.')
    
    P_LIST = new_p_list
    return msg_list


# Terminate all processes properly
def kill_process_list(p_list):
    global P_LIST
    new_p_list = []
    msg_list = []

    for pid, p_name in p_list:
        was_alive = psutil.pid_exists(pid)

        if was_alive:
            if IS_VERBOSE: print(f'{p_name} is ON, shutting it down... (PARENT_PID={pid})')
            
            # Kill the process and its children
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()

            # Check if the process and its children were indeed killed
            was_killed = psutil.pid_exists(pid)
        
        else:
            if IS_VERBOSE: print(f'{p_name} in P_LIST but OFF.')
            was_killed = False

        # Refresh the process list and set the response message
        if was_alive and was_killed:
            msg_list.append(f'{p_name} has been TURNED OFF.')
        elif was_alive and not was_killed:
            new_p_list.append((pid, p_name))
            msg_list.append(f'{p_name} is SHUTTING DOWN.')
        elif not was_alive:
            msg_list.append(f'{p_name} was already OFF.')

    P_LIST = new_p_list

    return msg_list


def select_UDP_port(host, init_port):
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while not a_socket.connect_ex((host, init_port)):
        init_port += 1
    if IS_VERBOSE: print(f'Port {init_port} chosen for UDP link.')
    return init_port


# def compute_SR_width(cam_idx, SR_height):
#     cap = cv2.VideoCapture(cam_idx)
#     time.sleep(2)

#     width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
#     height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    
#     if IS_VERBOSE: print (f'RATIO = {float(SR_height) / height}')
    
#     return width, height, int(width * SR_height / float(height))


class MyServer(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == '/start':
            self.do_START()
        elif self.path == '/stop':
            self.do_STOP()
        elif self.path == '/check':
            self.do_CHECK()


    def do_START(self):
        global P_LIST
        if IS_VERBOSE: print('P_LIST:', P_LIST)
        # Receive request
        n = int(self.headers['Content-Length'])
        data = self.rfile.read(n)
        request = json.loads(data)
        if IS_VERBOSE: print(request)
        msg_list = kill_process_list(P_LIST)
        info, p_args = self.gen_run_pipeline(request)
        response = {'request': "START",
                    'commands': p_args,
                    'info': msg_list + P_LIST + info}
        
        # Send a response to the client
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response_json = json.dumps(response)
        data = bytes(response_json, 'utf-8')
        self.wfile.write(data)


    def do_STOP(self):
        global P_LIST
        if IS_VERBOSE: print('P_LIST:', P_LIST)
        msg_list = kill_process_list(P_LIST)
        if len(msg_list) == 0:
            msg_list.append('NO MODULE RUNNING.')
        response = {'request': "STOP",
                    'info': msg_list}
        
        # Send a response to the client
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response_json = json.dumps(response)
        data = bytes(response_json, 'utf-8')
        self.wfile.write(data)


    def do_CHECK(self):
        global P_LIST
        if IS_VERBOSE: print('P_LIST:', P_LIST)
        msg_list = check_process_list(P_LIST)
        if len(msg_list) == 0:
            msg_list.append('NO MODULE RUNNING.')
        response = {'request': "CHECK",
                    'info': msg_list}
        
        # Send a response to the client
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response_json = json.dumps(response)
        data = bytes(response_json, 'utf-8')
        self.wfile.write(data)


    def gen_run_pipeline(self, json_conf):
        # webcam input with index support
        def _gen_webcam_in_file(webcam_idx):
            return f'--webcam --index={webcam_idx}'

        # ndi to appsink
        def _gen_NDI_in_file(input_NDI_name):
            return f'ndisrc ndi-name=\\\"{socket.gethostname()} ({input_NDI_name})\\\" ! ndisrcdemux name=demux demux.video ! queue ! videoconvert ! appsink'

        # ndi sink part of the gstreamer pipeline
        def _gen_NDI_sink(output_NDI_name):
            return f'ndisinkcombiner name=combiner ! videoconvert ! ndisink ndi-name={output_NDI_name}'

        # udp to appsink
        def _gen_UDP_in_file(port, fps):
            return f'udpsrc port={port} ! application/x-rtp,media=video,payload=26,clock-rate=90000,encoding-name=JPEG,framerate={fps}/1 ! rtpjpegdepay ! jpegdec ! videoconvert ! appsink'
        
        # udp sink part of the gstreamer pipeline
        def _gen_UDP_sink(host, port):
            return f'jpegenc ! rtpjpegpay ! udpsink host={host} port={port}'

        def _gen_BE_out_file(fps, BE_cmd_out_sink):
            return f"appsrc ! videoconvert ! video/x-raw,format=YUY2,framerate={fps}/1 ! {BE_cmd_out_sink}"

        def _gen_SR_out_file(fps, res_h, SR_cmd_out_sink):
            return f"appsrc ! video/x-raw, height={res_h}, framerate={fps}/1 ! {SR_cmd_out_sink}"

        def _gen_NVIDIA_MAXINE_BE_cmd(conf, fps, in_file, out_file, verbose, show, app_name=EXE_NAMES[0]):
            BE_m = f' --mode={conf["NVIDIA_MAXINE_mode"]}'
            BE_comp_m = f' --comp_mode={conf["comp_mode"]}'
            BE_custom_comp_m = f' --bgr=\"{conf["custom_comp_mode"]["blue"]},{conf["custom_comp_mode"]["green"]},{conf["custom_comp_mode"]["red"]}\"' if conf['comp_mode'] == 8 else ''

            BE_cmd = os.path.join(MAXINE_EXE_PATH, f'{app_name}.exe{verbose}{show} {in_file}{BE_comp_m}{BE_custom_comp_m}{BE_m} --fps={fps} --out_file="{out_file}"')
            if verbose: print(BE_cmd)
            return BE_cmd

        def _gen_MODNet_BE_cmd(conf, fps, in_file, output_stream_type, ndi_name, verbose, show):
            BE_comp_m = f' --comp_mode={conf["comp_mode"]}'
            BE_custom_comp_m = f' --bgr=\"{conf["custom_comp_mode"]["blue"]},{conf["custom_comp_mode"]["green"]},{conf["custom_comp_mode"]["red"]}\"' if conf['comp_mode'] == 8 else ''
            
            BE_cmd = f'python {MODNet_BE_PYTHON_SCRIPT_PATH} {in_file}{show} --fps={fps}{BE_comp_m}{BE_custom_comp_m} --output_stream={output_stream_type}{verbose} --ndi_name={ndi_name}'
            if verbose: print(BE_cmd)
            return BE_cmd

        def _gen_RVM_BE_cmd(conf, fps, in_file, output_stream_type, ndi_name, mode, shot, verbose, show):
            BE_comp_m = f' --comp_mode={conf["comp_mode"]}'
            BE_custom_comp_m = f' --bgr=\"{conf["custom_comp_mode"]["blue"]},{conf["custom_comp_mode"]["green"]},{conf["custom_comp_mode"]["red"]}\"' if conf['comp_mode'] == 8 else ''
            
            BE_cmd = f'python {RVM_BE_PYTHON_SCRIPT_PATH} {in_file}{show} --fps={fps}{BE_comp_m}{BE_custom_comp_m} --output_stream={output_stream_type}{verbose} --ndi_name={ndi_name} --mode={mode} --shot={shot}'
            if verbose: print(BE_cmd)
            return BE_cmd

        def _gen_SR_cmd(SR_conf, fps, SR_res, in_file, out_file, verbose, show, app_name=EXE_NAMES[1]):
            SR_m = f' --mode={SR_conf["mode"]}'
            SR_cmd = os.path.join(MAXINE_EXE_PATH, f'{app_name}.exe{verbose}{show} --effect=SuperRes{SR_m} --resolution="{SR_res}" --fps={fps} {in_file} --out_file="{out_file}"')
            if verbose: print(SR_cmd)
            return SR_cmd
        
        # Useful variables and strings
        verbose = ' --verbose' if IS_VERBOSE else ''
        show = ' --show' if IS_SHOW else ''

        webcam_idx = json_conf['webcam_index']

        link = json_conf['link']
        link_type = link['type']

        fps = json_conf['fps']
        output_NDI_name = json_conf['ndi_output']

        BE_conf = json_conf['background_extraction']

        SR_conf = json_conf['super_resolution']
        SR_height = SR_conf['resolution']

        p_args = []

        # If Background Extraction is enabled
        if BE_conf['enabled']:
            BE_module_choice = BE_conf["choice"]
            
            # Generate the BE input arguments
            BE_in_file = _gen_webcam_in_file(webcam_idx)

            # Generate the BE output arguments
            # - If SR is also enabled, the output of BE module is either a NDI or a UDP stream
            if SR_conf["enabled"]:
                if link_type == 'NDI':
                    NDI_link_name = link["NDI_name"]
                    BE_cmd_out_sink = _gen_NDI_sink(output_NDI_name=NDI_link_name)
                    ndi_name = NDI_link_name
                elif link_type == 'UDP':
                    UDP_host = link["UDP"]["host"]
                    UDP_port = select_UDP_port(host=UDP_host, init_port=int(link["UDP"]["port"]))
                    BE_cmd_out_sink = _gen_UDP_sink(host=UDP_host, port=UDP_port)
            
            # - Else, we are running the BE alone, so the output should always be NDI with ndi_output parameter as name
            else:
                BE_cmd_out_sink = _gen_NDI_sink(output_NDI_name=output_NDI_name)
                ndi_name = output_NDI_name
                link_type = 'NDI'

            BE_out_file = _gen_BE_out_file(fps, BE_cmd_out_sink)
            
            # Generate the full BE command depending on the chosen module, with input and output arguments previously created
            if BE_module_choice == BE_MODULE_NAMES[0]:
                BE_cmd = _gen_NVIDIA_MAXINE_BE_cmd(BE_conf, fps, BE_in_file, BE_out_file, verbose, show)
            
            elif BE_module_choice == BE_MODULE_NAMES[1]:
                BE_cmd = _gen_MODNet_BE_cmd(BE_conf, fps, BE_in_file, str.lower(link_type), ndi_name, verbose, show)
            
            elif BE_module_choice == BE_MODULE_NAMES[2]:
                RVM_mode = BE_conf["RVM_mode"]
                RVM_shot = BE_conf["RVM_shot"]
                BE_cmd = _gen_RVM_BE_cmd(BE_conf, fps, BE_in_file, str.lower(link_type), ndi_name, RVM_mode, RVM_shot, verbose, show)
            
            # Launch the BE command and it to the p_args list and to the pid list for later termination
            p = Popen(BE_cmd, bufsize=1, universal_newlines=True, shell=True)
            p_args.append(p.args)
            P_LIST.append((p.pid, 'BACKGROUND_EXTRACTION_' + BE_module_choice))

            # If the SR module (always Maxine) is enabled,
            
            # Wait for 10 seconds for the Background Extraction to start
            time.sleep(10)
            if SR_conf['enabled']:

                # Generate the input argument of the SR command depending on the link type, 
                if link_type == 'NDI':
                    SR_in_file = _gen_NDI_in_file(input_NDI_name=NDI_link_name)
                elif link_type == 'UDP':
                    SR_in_file = _gen_UDP_in_file(port=UDP_port, fps=fps)
                
                SR_in_file = f'--in_file="{SR_in_file}"'
                # _, h, SR_width = compute_SR_width(cam_idx, SR_height)
                SR_out_file = _gen_SR_out_file(fps, SR_height, SR_cmd_out_sink=_gen_NDI_sink(output_NDI_name))
                SR_cmd = _gen_SR_cmd(SR_conf, fps, SR_height, SR_in_file, SR_out_file, verbose, show)

                p = Popen(SR_cmd, bufsize=1, universal_newlines=True, shell=True)
                p_args.append(p.args)
                P_LIST.append((p.pid, 'SUPER_RESOLUTION_' + BE_MODULE_NAMES[0]))

        # Else, if the SR module is enabled, it is enabled alone
        # So it should take the webcam as input
        # And output an NDI stream with the specified NDI name
        elif SR_conf['enabled']:
            SR_in_file = _gen_webcam_in_file(webcam_idx)
            # _, h, SR_width = compute_SR_width(cam_idx, SR_height)
            SR_out_file = _gen_SR_out_file(fps, SR_height, SR_cmd_out_sink=_gen_NDI_sink(output_NDI_name))
            SR_cmd = _gen_SR_cmd(SR_conf, fps, SR_height, SR_in_file, SR_out_file, verbose, show)
            p = Popen(SR_cmd, bufsize=1, universal_newlines=True, shell=True)
            p_args.append(p.args)
            P_LIST.append((p.pid, 'SUPER_RESOLUTION_' + BE_MODULE_NAMES[0]))

        else:
            error_str = "ERROR: At least one of the modules should be set to enabled in the JSON configuration file."
            if IS_VERBOSE: print(error_str)
            return [error_str], []

        return [''], p_args



if __name__ == '__main__':
    server = http.server.HTTPServer((HOST, PORT), MyServer)
    print('Listening on http://%s:%s' % (HOST, PORT))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    server.server_close()
