import argparse
import os
import time
from threading import Lock, Thread

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from model import MattingNetwork

RESNET50_CKPT_PATH = (f"C:/Users/{os.getlogin()}/Documents/AdMiRe/src/"
                      "be_sr_modules/robust_video_matting/checkpoints/"
                      "rvm_resnet50.pth")
MOBILENETV3_CKPT_PATH = (f"C:/Users/{os.getlogin()}/Documents/"
                         "AdMiRe/src/be_sr_modules/robust_video_matting/"
                         "checkpoints/rvm_mobilenetv3.pth")

# ----------- Utility classes -------------


class Camera:
    """
    A wrapper that reads data from cv2.VideoCapture
    in its own thread to optimize.
    Use .read() in a tight loop to get the newest frame.
    """

    def __init__(self, device_id=1):
        self.capture = cv2.VideoCapture(device_id)
        self.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        self.success_reading, self.frame = self.capture.read()
        self.read_lock = Lock()
        self.thread = Thread(target=self.__update, args=())
        self.thread.daemon = True
        self.thread.start()

    def __update(self):
        while self.success_reading:
            grabbed, frame = self.capture.read()
            with self.read_lock:
                self.success_reading = grabbed
                self.frame = frame

    def read(self):
        with self.read_lock:
            frame = self.frame.copy()
        return frame

    def __exit__(self, exec_type, exc_value, traceback):
        self.capture.release()


class FPSTracker:
    """
    An FPS tracker that computes exponentialy moving average FPS.
    """

    def __init__(self, ratio=0.5):
        self._last_tick = None
        self._avg_fps = None
        self.ratio = ratio

    def tick(self):
        if self._last_tick is None:
            self._last_tick = time.time()
            return None
        t_new = time.time()
        fps_sample = 1.0 / (t_new - self._last_tick)
        self._avg_fps = self.ratio * fps_sample + (1 - self.ratio) * \
            self._avg_fps if self._avg_fps is not None else fps_sample
        self._last_tick = t_new
        return self.get()

    def get(self):
        return self._avg_fps


class Displayer:
    """
    Wrapper for playing a stream with cv2.imshow().
    It also tracks FPS and optionally overlays info onto the stream.
    """

    def __init__(self, title, width=None, height=None, show_info=True):
        self.title, self.width, self.height = title, width, height
        self.show_info = show_info
        self.fps_tracker = FPSTracker()
        cv2.namedWindow(self.title, cv2.WINDOW_NORMAL)
        if width is not None and height is not None:
            cv2.resizeWindow(self.title, width, height)

    # Update the currently showing frame and return key press char code
    def step(self, image):
        fps_estimate = self.fps_tracker.tick()
        if self.show_info and fps_estimate is not None:
            message = f"{int(fps_estimate)} fps | {self.width}x{self.height}"
            cv2.putText(image, message, (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0))
        cv2.imshow(self.title, image)
        return cv2.waitKey(1) & 0xFF


def cv2_frame_to_cuda(frame):
    """
    convert cv2 frame to tensor.
    """
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    loader = transforms.ToTensor()
    return loader(Image.fromarray(frame)).to(
        device, dtype, non_blocking=True).unsqueeze(0)


def auto_downsample_ratio(h, w):
    """
    Automatically find a downsample ratio so that
    the largest side of the resolution be 512px.
    """
    return min(512 / max(h, w), 1)


# --------------- Main ---------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--webcam', action="store_true", help="use webcam feed as input")
    parser.add_argument(
        '--index', type=int, default=1,
        help='index to select desired webcam')
    parser.add_argument(
        '--fps', type=int, default=25, help='fps of the result video')
    parser.add_argument(
        '--show', action='store_true', help='show output on opencv window')
    parser.add_argument(
        '--output_stream', type=str, default='udp',
        choices=['udp', 'ndi'])
    parser.add_argument(
        '--comp_mode', type=int, default=2,
        help='background in output composition',
        choices=[2, 7, 8])
    parser.add_argument('--ndi_name', type=str, default='AdMiRe',
                        help='name of the output ndi stream')
    parser.add_argument('--udp_ip', type=str, default='127.0.0.1')
    parser.add_argument('--udp_port', type=str, default='5000')
    parser.add_argument('--bgr', type=str, default='100,0,200',
                        help='bbb,ggg,rrr values for comp_mode 8')
    parser.add_argument('--verbose', action='store_true',
                        help='print info to console')
    parser.add_argument(
        '--mode', type=int, default=1, help='0 for performance '
        'with MobileNetV3, 1 for quality with ResNet50',
        choices=[0, 1])
    parser.add_argument(
        '--shot', type=str, default=None,
        choices=[None, "portrait", "full_body"],
        help="type of shot: head and shoulders (portrait) or full body"
    )
    args = parser.parse_args()
    fps = args.fps
    ndi_name = args.ndi_name
    dtype = torch.float32
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    if (args.mode == 0):
        model = MattingNetwork('mobilenetv3')
        ckpt_path = MOBILENETV3_CKPT_PATH
    if (args.mode == 1):
        model = MattingNetwork('resnet50')
        ckpt_path = RESNET50_CKPT_PATH
    model = model.to(device, dtype, non_blocking=True).eval()
    model.load_state_dict(torch.load(ckpt_path))
    model = torch.jit.script(model)
    model = torch.jit.freeze(model)
    cam = Camera(args.index)
    width = cam.width
    height = cam.height
    if (args.show):
        dsp = Displayer('VideoMatting', width, height, show_info=True)
    if (args.output_stream == "ndi"):
        writer = cv2.VideoWriter(
                        f"""appsrc ! videoconvert ! video/x-raw,format=YUY2,framerate={fps}/1 ! \
                        ndisinkcombiner name=combiner ! \
                        videoconvert ! ndisink ndi-name={ndi_name}""",
                        0, fps, (width, height))
    if (args.output_stream == "udp"):
        writer = cv2.VideoWriter(
                        f"""appsrc ! videoconvert ! video/x-raw,format=YUY2,framerate={fps}/1 ! \
                        jpegenc ! rtpjpegpay ! \
                        udpsink host={args.udp_ip} port={args.udp_port}""",
                        0, fps, (width, height))
    bgr = None
    if args.comp_mode == 2:  # green background
        bgr = torch.tensor([0, 255, 0], device=device,
                           dtype=dtype).div(255).view(3, 1, 1)
    if args.comp_mode == 7:  # blue background
        bgr = torch.tensor([0, 0, 255], device=device,
                           dtype=dtype).div(255).view(3, 1, 1)
    if args.comp_mode == 8:  # custom background
        b, g, r = args.bgr.split(',')
        b = int(b)
        g = int(g)
        r = int(r)
        assert b >= 0 and b <= 255, "Please insert a b value between 0 and 255"
        assert g >= 0 and g <= 255, "Please insert a g value between 0 and 255"
        assert r >= 0 and r <= 255, "Please insert a r value between 0 and 255"
        bgr = torch.tensor([r, g, b], device=device,
                           dtype=dtype).div(255).view(3, 1, 1)

    with torch.no_grad():
        while True:
            # matting
            frame = cam.read()
            src = cv2_frame_to_cuda(frame)
            rec = [None] * 4
            if not args.shot:
                downsample_ratio = auto_downsample_ratio(*src.shape[2:])
            # recommended for portrait when input resolution is 1280x720:
            if args.shot == "portrait":
                downsample_ratio = 0.375
            # recommended for full-body when input resolution 1280x720:
            if args.shot == "full_body":
                downsample_ratio = 0.6
            fgr, pha, *rec = model(src, *rec, downsample_ratio)
            com = fgr * pha + bgr * (1 - pha)
            com = np.uint8(
                com.mul(255).byte().cpu().permute(0, 2, 3, 1).numpy()[0])
            com = cv2.cvtColor(com, cv2.COLOR_RGB2BGR)
            writer.write(com)
            if args.show:
                key = dsp.step(com)
                if key == ord('b'):
                    break
                elif key == ord('q'):
                    exit()
