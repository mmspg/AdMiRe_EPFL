import argparse
import time
import os

import cv2
import kornia as K
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as transforms

from models.modnet import MODNet

# For input size 1280x720
NN_WIDTH = 896
NN_HEIGHT = 512
MODEL_PATH = (f"C:/Users/{os.getlogin()}/Documents/AdMiRe/src/be_sr_modules/"
              "MODNet/pretrained/modnet_photographic_portrait_matting.ckpt")


def matting(webcam: int, fps: float, show: bool, output: str, comp_mode: int,
            ndi_name: str, udp_ip: str, udp_port: str,
            bgr: str, verbose: bool):
    _fps = False
    times = []
    bg = np.zeros((NN_HEIGHT, NN_WIDTH, 3))
    # Green
    if (comp_mode == 2):
        bg[:, :, 1] = 1
    # Blue
    if (comp_mode == 7):
        bg[:, :, 2] = 1
    # Custom color (bbb,ggg,rrr)
    if (comp_mode == 8):
        b, g, r = bgr.split(',')
        bg[:, :, 0] = float(r) / 255.
        bg[:, :, 1] = float(g) / 255.
        bg[:, :, 2] = float(b) / 255.
    bg = transforms.ToTensor()(bg).cuda()
    # Initialize webcam
    vc = cv2.VideoCapture(webcam)
    if vc.isOpened():
        rval, frame = vc.read()
    else:
        rval = False
    tic = time.perf_counter()
    while (not rval):
        rval, frame = vc.read()
        tac = time.perf_counter()
        if (tic-tac > 5):
            print(f"Can't read frames from webcam with index {webcam}")
            print("Exiting...")
            exit()
    # Adjust size of input frame for BE model
    h, w = frame.shape[:2]
    if w >= h:
        rh = 512
        rw = int(w / h * 512)
    else:
        rw = 512
        rh = int(h / w * 512)
    rh = rh - rh % 32
    rw = rw - rw % 32
    print(f"Width to nn: {rw}, height to nn {rh}")
    if (output == 'udp'):
        writer = cv2.VideoWriter(
                        f"""appsrc ! videoconvert ! video/x-raw,format=YUY2,framerate={fps}/1 ! \
                        jpegenc ! rtpjpegpay ! \
                        udpsink host={udp_ip} port={udp_port}""",
                        0, fps, (NN_WIDTH, NN_HEIGHT))
    if (output == 'ndi'):
        writer = cv2.VideoWriter(
                        f"""appsrc ! videoconvert ! video/x-raw,format=YUY2,framerate={fps}/1 ! \
                        ndisinkcombiner name=combiner ! \
                        videoconvert ! ndisink ndi-name={ndi_name}""",
                        0, fps, (NN_WIDTH, NN_HEIGHT))
    print('Start matting...')
    while(rval):
        tic = time.perf_counter()
        frame_tensor = transforms.ToTensor()(frame).cuda()
        frame_tensor = frame_tensor.unsqueeze(0)
        frame_tensor = K.color.bgr_to_rgb(frame_tensor)
        frame_tensor = transforms.Resize((NN_HEIGHT, NN_WIDTH))(frame_tensor)
        frame_tensor_n = transforms.Normalize((0.5, 0.5, 0.5),
                                              (0.5, 0.5, 0.5))(frame_tensor)
        with torch.no_grad():
            _, _, matte_tensor = BE_Net(frame_tensor_n, True)
        matte_tensor = matte_tensor.repeat(1, 3, 1, 1)
        matte_tp = matte_tensor[0].data
        view_np = matte_tp * frame_tensor.squeeze(0) + (1 - matte_tp) * bg
        view_np = np.uint8((view_np * 255.).permute(1, 2, 0).cpu().numpy())
        view_np = view_np[:, :, ::-1]
        writer.write(view_np)
        tac = time.perf_counter()
        times.append(tac-tic)
        if show:
            if cv2.waitKey(1) & 0xFF == ord('f'):
                _fps = not _fps
                if(_fps):
                    print("Showing fps")
            if _fps:
                fps = 1 / np.average(times[-30:])
                view_np = cv2.putText(view_np, f"fps:{fps:.2f}", (50, 50),
                                      cv2.FONT_HERSHEY_PLAIN,
                                      color=(0, 0, 255),
                                      fontScale=1, thickness=2)
                if (verbose):
                    print(fps)
            cv2.imshow('WebCam [Press \'Q\' To Exit]', view_np)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        rval, frame = vc.read()
    print('Exiting...')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--webcam', action='store_true', help='select webcam as input')
    parser.add_argument(
        '--index', type=int, help='index of the desired webcam',
        default=0)
    parser.add_argument(
        '--fps', type=int, default=25, help='fps of the result video')
    parser.add_argument(
        '--model_path', type=str,
        default=MODEL_PATH,
        help='path to the model')
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

    print('Parsing arguments...')
    args = parser.parse_args()
    print('Loading the Model...')
    pretrained_ckpt = args.model_path
    BE_Net = MODNet(backbone_pretrained=False)
    BE_Net = nn.DataParallel(BE_Net)
    GPU = True if torch.cuda.device_count() > 0 else False
    if GPU:
        print('Using GPU...')
        BE_Net = BE_Net.cuda()
        BE_Net.load_state_dict(torch.load(pretrained_ckpt))
    else:
        print('Using CPU...')
        BE_Net.load_state_dict(torch.load(pretrained_ckpt,
                               map_location=torch.device('cpu')))
    BE_Net.eval()
    matting(args.index, args.fps, args.show, args.output_stream,
            args.comp_mode, args.ndi_name, args.udp_ip, args.udp_port,
            args.bgr, args.verbose)
