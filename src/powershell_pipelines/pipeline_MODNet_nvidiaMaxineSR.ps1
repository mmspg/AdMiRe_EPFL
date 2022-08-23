param([string]$index_val=1, [string]$comp_mode_val=2, [string]$fps=25, [string]$user=$env:UserName, [string]$output="udp")
Start-Process -FilePath "python" -ArgumentList """C:\Users\$user\Documents\AdMiRe\src\be_sr_modules\MODNet\run.py"" --webcam --index=$index_val --output=$output --fps=$fps --comp_mode=$comp_mode_val"
if ($output -eq "udp")
{
    $in_file = """udpsrc port=5000 ! application/x-rtp,media=video,payload=26,clock-rate=90000,encoding-name=JPEG,framerate=$fps/1 ! rtpjpegdepay ! jpegdec ! videoconvert ! appsink"""
}
if ($output -ne "udp")
{
    $hostname = HOSTNAME.EXE
    $in_file = """ndisrc ndi-name=\""$hostname (be)\""! ndisrcdemux name=demux demux.video ! queue ! videoconvert ! appsink"""
}
$args_1 = "--fps=$fps --in_file=$in_file --effect=SuperRes --resolution=1536 --show --out_file=""appsrc ! video/x-raw, width=2688, height=1536 ! ndisinkcombiner name=combiner ! videoconvert ! ndisink ndi-name=""BE_SR_output"""""
Start-Process -FilePath "C:\Users\$user\MAXINE-VFX-SDK-master-OSS\build\Release\VideoEffectsApp.exe" -ArgumentList $args_1