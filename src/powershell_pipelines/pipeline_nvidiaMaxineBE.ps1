param([string]$index_val=1, [string]$comp_mode_val=2, [string]$user=$env:UserName)
$arg_list =  "--comp_mode=$comp_mode_val " + "--index=$index_val "  + '--webcam --out_file="appsrc ! video/x-raw ! ndisinkcombiner name=combiner ! videoconvert ! ndisink ndi-name="BG_extraction_output" ' 
Start-Process -FilePath "C:\Users\$user\MAXINE-VFX-SDK-master-OSS\build\Release\AigsEffectApp.exe" -ArgumentList $arg_list