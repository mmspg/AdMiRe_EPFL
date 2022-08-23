param([string]$index_val=1, [string]$comp_mode_val=2, [string]$fps=25, [string]$user=$env:UserName)
$tmp_ndi_name = "BE"
$hostname = hostname.exe
$args_0 = "--comp_mode=$comp_mode_val --index=$index_val --fps=$fps --webcam  --out_file=""appsrc ! videoconvert ! video/x-raw,format=YUY2,framerate=$fps/1 ! ndisinkcombiner name=combiner ! videoconvert ! ndisink ndi-name=$tmp_ndi_name"""
$args_1 = "--show --fps=$fps --in_file=""ndisrc ndi-name=\""$hostname ($tmp_ndi_name)\""! ndisrcdemux name=demux demux.video ! queue ! videoconvert ! appsink"" --effect=SuperRes --resolution=1080 --out_file=""appsrc ! video/x-raw, width=1920, height=1080 ! ndisinkcombiner name=combiner ! videoconvert ! ndisink ndi-name=""BE_SR"""""
Start-Process -FilePath "C:\Users\$user\MAXINE-VFX-SDK-master-OSS\build\Release\AigsEffectApp.exe" -ArgumentList $args_0
Start-Sleep -Seconds 2
Start-Process -FilePath "C:\Users\$user\MAXINE-VFX-SDK-master-OSS\build\Release\VideoEffectsApp.exe" -ArgumentList $args_1

