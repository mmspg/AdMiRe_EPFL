# BE - SR configuration

## Input settings

`webcam_index` [Positive Integer]: Index of the desired webcam, e.g `0`

## Background Extraction modules

`enabled` [Boolean]: `true` or `false`

`choice` [String]: `"NVIDIA_MAXINE"` or `"MODNet"` or `"RVM"`

`NVIDIA_MAXINE_mode` [Integer]: `0` (Best quality) or `1` (Fastest performance)

`RVM_mode` [Integer]: `0` (Performance) or `1` (Quality)

`RVM_shot` [String]: `"portrait"` or `"full_body"`

`comp_mode` [Integer]: `0` (compMatte), `1` (compLight), `2` (compGreen), `3` (compWhite), `4` (compNone), `5` (compBG), `6` (compBlur), `7` (compBlue), or `8` (custom). /!\  Only `2`, `7`, `8` work when `choice` above is `"MODNet"`.

`custom_comp_mode` (only used if `comp_mode` above is 8)
- `blue` [Positive Integer]: B component, max = `255`, e.g `123`
- `green` [Positive Integer]: G component, max = `255`, e.g `123`
- `red` [Positive Integer]: R component, max = `255`, e.g `123`

## Link between modules

`link` (this part is only used when there is a Background extraction module and a Super Resolution module enabled)
- `type` [String]: `"NDI"` (the output of the first module is a NDI stream - may introduce latency / frame drops because of raw frames transmission) or `"UDP"` (the output of the first effect is a UDP stream - requires an additional encoding/decoding step which may lead to video quality and module output quality losses)
- `NDI_name` [String]: if `"NDI"` was selected in `type` above, this sets the name of the intermediary NDI stream (the output stream from the Background Extraction module)
- `UDP` (only used if `"UDP"` was selected in `type` above)
    - `host` [String]: the address where the UDP stream was sent, e.g `"127.0.0.1"`
    - `port` [Integer]: the port number that was used to create the UDP stream, e.g `5000`

## Super Resolution module

`enabled` [Boolean]: `true` or `false`

`mode` [Integer]: `0` (Weak enhancement and reduces encoding artifacts) or `1` (Strong enhancements)

`resolution` [Integer]:
- If `choice` above in Background Extraction section is `"NVIDIA_MAXINE"` or `"RVM" , possible resolutions are `1080`, `1440`, and `2160`. Same possible resolutions in the case where Background Extraction is completely `disabled`, assuming that the webcam input is 720p high with a 16:9 aspect ratio.
- If `choice` above in Background Extraction section is `"MODNet"`, possible resolutions are `1024`, `1536`, and `2048`

## Final settings

`ndi_output` [String]: name of the final NDI stream, e.g `"AdMiRe"`

`fps` [Positive Integer]: Number of frames per second desired in the final result, e.g `25`
