|                                  [screw hole]                                          |
| Label A              | Pin A  | Phys A | Phys B | Pin B  | Label B                     |
|----------------------|--------|--------|--------|--------|-----------------------------|
| 3.3V (red wire)      | 3.3V   | 1      | 2      | 5V     |                             |
|                      | GPIO2  | 3      | 4      | 5V     |                             |
|                      | GPIO3  | 5      | 6      | GND    | GND (black)                 |
| TM_DIO (grey)        | GPIO4  | 7      | 8      | GPIO14 |                             |
| GND (black)          | GND    | 9      | 10     | GPIO15 |                             |
| MAIN_BTN  (red)      | GPIO17 | 11     | 12     | GPIO18 |                             |
|                      | GPIO27 | 13     | 14     | GND    |                             |
|                      | GPIO22 | 15     | 16     | GPIO23 | MUX1 (C / 9, orange)        |
|                      | 3.3V   | 17     | 18     | GPIO24 | MUX2 (B / 10, yellow)       |
|                      | GPIO10 | 19     | 20     | GND    |                             |
|                      | GPIO9  | 21     | 22     | GPIO25 | MUX3 (A / 11, green)        |
|                      | GPIO11 | 23     | 24     | GPIO8  | MUX_IN (blue)               |
|                      | GND    | 25     | 26     | GPIO7  |                             |
|                      | GPIO0  | 27     | 28     | GPIO1  |                             |
| TM_CLK  (purple)     | GPIO5  | 29     | 30     | GND    |                             |
| BTN_BLUE             | GPIO6  | 31     | 32     | GPIO12 | LED_BLUE                    |
| BTN_GREEN            | GPIO13 | 33     | 34     | GND    |                             |
| BTN_YELLOW           | GPIO19 | 35     | 36     | GPIO16 | LED_GREEN                   |
| BTN_RED (orange)     | GPIO26 | 37     | 38     | GPIO20 | LED_YELLOW                  |
|                      | GND    | 39     | 40     | GPIO21 | LED_RED (orange)            |
|                                 [usb ports]                                            |


**Legend:**
- `btnRed`, `btnYellow`, `btnGreen`, `btnBlue`: User buttons
- `ledRed`, `ledYellow`, `ledGreen`, `ledBlue`: LEDs
- `mainBtn`: Main "Go" button
- `mux1`, `mux2`, `mux3`, `muxIn`: Multiplexer pins for reading toggle switches
- `tm1637 CLK`, `tm1637 DIO`: 7-segment display
- All GND and 3.3V/5V pins must be connected as per hardware requirements

**Refer to the table in docs.md for exact pin assignments and wire colours.**





