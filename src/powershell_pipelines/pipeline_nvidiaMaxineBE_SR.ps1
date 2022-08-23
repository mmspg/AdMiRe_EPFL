param([string]$index_val=1, [string]$comp_mode_val=2,[string]$fps=25,[string]$user=$env:UserName)
$args_0 =  "--comp_mode=$comp_mode_val --index=$index_val --fps=$fps --webcam --out_file=""appsrc ! videoconvert ! video/x-raw,format=YUY2,framerate=$fps/1 ! jpegenc ! rtpjpegpay ! udpsink host=127.0.0.1 port=5001""" 
$args_1 = "--fps=$fps --in_file=""udpsrc port=5001 ! application/x-rtp,media=video,payload=26,clock-rate=90000,encoding-name=JPEG,framerate=$fps/1 ! rtpjpegdepay ! jpegdec ! videoconvert ! appsink"" --effect=SuperRes --resolution=1080 --show --out_file=""appsrc ! video/x-raw, width=1920, height=1080 ! ndisinkcombiner name=combiner ! videoconvert ! ndisink ndi-name=""BG_extraction_+_SR_output"""""
Start-Process -FilePath "C:\Users\$user\MAXINE-VFX-SDK-master-OSS\build\Release\AigsEffectApp.exe" -ArgumentList $args_0
Start-Sleep -Seconds 2
Start-Process -FilePath "C:\Users\$user\MAXINE-VFX-SDK-master-OSS\build\Release\VideoEffectsApp.exe" -ArgumentList $args_1