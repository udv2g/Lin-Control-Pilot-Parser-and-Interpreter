# Lin Control Pilot Parser and Interpreter
[SAE J3068](https://www.sae.org/search/?qt=j3068) interpretation\
CVORG / The University of Delaware   
By Colden Rother and Dr. Ejzak

## Introduction

![](README_images/LINGUI_Poster-1.png)

This project focuses on displaying Local Interconnected Network(LIN) protocol communications transmitted through the Control Pilot (CP) wire between an Electric Vehicle (EV) and Supply Equipment (SE). This is achieved by using the LIN-Tool (PCB), which directly reads Binary data from the CP wire. Users can connect to the LIN-Tool via USB, linking it to the serial port on their computer to interpret live LIN traffic through the provided GUI. The setup requires three connections: Control Pilot, Ground, and a USB connection to the serial port on the user's device. Using the GUI, users can interpret the LIN conversation in real time or from previously saved files between the EV and SE.

This is a hardware and software implementation of the communications is in the (LIN-CP) portion of [SAE J3068 series](https://en.wikipedia.org/wiki/SAE_J3068#Digital_Communication_for_AC_charging_%28LIN-CP%29).

---
## Recent Updates

- Added Support for SAE J3068, SAE J3068/1, and SAE J3068/2 [**NOTE** SAE J3068/2 may have bugs please report any that do not adhere to the standard this is currently under development] 
- CRC32 check for multiplexed frames implemented into debug log.
- Added support for Python Code Gen from [here](https://github.com/udv2g/saej3068-emulator). Directions on how to change the parameters for what multiplexed frames are included and how to generate the code look at the link in the previous sentence. 

## Future Updates

- Make CRC32 check part of GUI to show matches and mismatches in color
- update GUI to be more user friendly
- add more to dropdown boxes as SAE J3068 series Standard progresses
---

## Software/GUI
The GUI has a multifunctional design to carry out a variety of tasks including parsing various LIN communication configurations from saved files, as well as live binary directly from CP line. The overall goal is to be able to interpret different communications and decisions being made between the EVSE during their synchronization.

### Prerequisites
There is 2 options for running this program.  <br><br>**1. [Only use if you have a Windows devices]** navigate to where you downloaded the program. Then follow this path dist\main\ in this location you should see 2 things a file that is _internal and another main.exe, double-click on main.exe. The program should now be working. This method doesn't require you to have any pre-downloaded items such as Python or specific libraries. <br>
<br>**2. [Non-Windows devices/Windows Development]** Before running the application, ensure you have the following installed on your system:

- **Python 10+ Required**  
  This application was tested on [Python Version 3.13.5](https://www.python.org/downloads/).

- **PyQt5**  
  The GUI uses the PyQt5 framework. Install it:
  ```bash
  install PyQt5
  ```

- **pyserial**  
  For handling live serial data, the application uses `pyserial`. Install it:
  ```bash
  install pyserial
  ```

- **Other Standard Libraries**  
  The code utilizes standard Python libraries such as `os`, `ctypes`, `re`, `copy`, `queue`, etc., which come with the standard Python distribution.

---

### Usage

1. **Run the Application**  
   Navigate to wherever you installed the files on powershell, CMD, or whatever IDE you use and execute main.py to start the GUI:
   ```bash
   # CMD or Powershell run this when in project directory 
   py main.py     # Python Version 3.13.5
   python main.py # if previouse call didn't work try this
   ```

2. **Main Interface Overview**  
   - **Top Bar Controls:**
     - **File Button:** Click to select and parse a LIN data file.
     - **Debug Button:** Open a debug window to view debug information, and see buffer frames.
     - **Live Data Toggle:** Toggle live data mode on/off. When activating, choose a serial port to start reading live data. Also, specify the amount of buffer frames you want. This defaults to 100 frames automatically if unspecified.
     - **Frame or Frame Timing Toggle:** This toggles between the GUI showing what time it received the frame and showing the most recent frame number the data came from.
     - **Reset Timer:** This allows you to sets a 0 point based on where the slider is located when pressed.
     - **Toggle N/A's for ID stages and Data stages:** This is defaulted to off, but when enabled hides all N/A valued data in EvID, SeID, EvData, and SeData.
     - **Save Log Button:** Save the logged live data to a text file to be able to be put through file parser at a later time. This saves the binary data into Hexadecimal.
     - **Trash Bin Button:** Clear all displayed and parsed data.
     
   - **Slider and Frame Navigation:**
     - Drag the slider to navigate through frames. The slider shows the current frame and whether it is valid.
     - Buttons around the slider allow frame-by-frame navigation, jumping to start/end frames, or directly inputting a frame number.
	 - If the slider is selected, you may use the appropriate arrow keys to move the slider to the desired location
	 - When in Live Mode the slider will move to show the newest frame coming in. To disable this click the slider or any arrow other than the skip to the end arrow. This arrow re-enables the slider to show the newest incoming frame.
   
   - **Data Display Sections:**
     - **Overview:** The left side of the GUI is mainly SAE J3068 except for the control page drop down and the bottom data in task, this is a part of SAE J3068/1. The right side tabs all belong to SAE J3068/1 as well in the schedule known as OP3.
	 - **NOTE:** If any of the fonts are too big for your screen simpy hover your mouse over the area of issue and hold control and use two fingers on the trackpad or scroll wheel going up or down to change the text size.
	
3. **Parsing a File:**
   - Click the **File Button** to open a file selection dialog.
   - Select the desired LIN data file (text or binary or log).
   - A format selection dialog will appear, the program will guess the type of file you have selected. If it is right hit OK or Enter, if not select your file type.
   - Enter desired amount of buffer frames defaults to 100.
   - After selection, the file is parsed, and data is visualized across frames using the slider. 
   - Be sure to wait about 30 seconds some bigger files take longer than others. During this a loading screen will occur. If the loading screen has not disappeared from your screen it has not finished parsing your file even if things are happening while the loading screen is still on screen.
   
4. **Debug Information:**
   - This window should be your go to when encountering errors within the program such as live data errors, serial port errors, and file parse errors. This also is where you can get a more in depth look of each frame and its determination of a valid frame such as checksum checks, Protected Identifier checks, and information bytes.
   - When encountering an invalid frame this window will show the justification for it being classified as such. These classifications are explained later in this document.
     - **Debug Info Tab:** This has a search bar at the top to search for specific frames. (This doesn't auto update data when line must close and reopen debug log to get the newest debug information)
     - **Recent Data Tab:** This displays the users buffer frames(The most recent amount of frames received specified by user.) in real time showing the average time between their own frame type and how many there are. This also comes with the capability to see if unspecified frames that are coming through such as ones not specified in the [SAEJ3068 series](https://en.wikipedia.org/wiki/SAE_J3068#Digital_Communication_for_AC_charging_%28LIN-CP%29) documents. It will display the frame type number it is receiving.

5. **Live Data Mode:**
   - Toggle the **Live Data Button** to switch on live data mode.
   - Select a serial port when prompted.
   - The application will read binary data from the serial port, parse LIN frames in real-time, and update the displays.
   - To stop live data mode, toggle the button off.
   - Also allows user to specify amount of buffer frames user wants Default is 100.
   - **Note** This application reads the serial port at 19200 Baud.
   
6. **Frame or Frame Timing Toggle:**
   - This toggle automatically turns on when live data is on. This shows the time the frame was received when live data is being read. When toggled off it shows which most recent frame that data was pulled from.
   
7. **Reset Timer:**
   - This allows you to set a time 0 when reading live data, meaning lets say 100 frames were transmitted in 60 seconds. 
   - If you drag the slider to frame 50 then hit the reset timer button, frame 50 will now be time 0s. Then frame 100 would be 30s, and frame 0 will be -30s.
8. **Toggle N/A's for ID stages and Data stages:**
   - This is defaulted to off
   - When enabled hides all N/A valued data in EvID, SeID, EvData, and SeData.
   - This is helpful to hide large amounts of non-transmitted data

9. **Saving Logs:**
   - Click the **Save Log Button** to save the live data log to a text file after desired amount of data has already come in. 
   - This save file can now be parsed through the file parser.
   - This is extremely powerful for taking a reading off a vehicle on one site and sending to another person via email to interpret with the parser on their side for analysis of the vehicle.

10. **Clear Data:**
    - Click the **Trash Bin Button** and confirm to clear all parsed data and reset the application state.
    - This can be helpful when doing new tests so you don't have to re-open the application again.

---

## Lin Tool PCB
The hardware design is provided as a schematic and PCB layout that are in KiCad format. KiCad can be downloaded [here](https://www.kicad.org/). The PCB, as mentioned above, directly reads from the CP line and allows users to access these signals on their computer via the serial port.

To order the PCB, we recommend using [JLCPCB](https://jlcpcb.com/). JLCPCB not only prints your custom circuit board but also assembles all the components on the chip, provided they are compatible with their inventory. This design was made using their in stock parts at the time. Directions on how to order a PCB using a gerber file can be found [here](https://jlcpcb.com/help/article/how-do-I-place-a-layout-order). JLCPCB is a trusted PCB manufacturer and a cost-effective option. However, please note that the PCB will ship directly from China and may take up to a week to arrive.



### Parts List

| Quantity | Identifier  | Description       | Example Part Number(s) |
|----------|-------------|-------------------|------------------------|
| 1        | J1          | USB component     | C456014                |
| 1        | U1          | USB to serial chip | CH340B                 |
| 1        | U2          | Voltage doubler   | MAX1682                |
| 1        | U3          | LIN bus transceiver | TJA1021T               |
| 1        | U4          | LDO regulator     | AM51117                |
| 4        | C1,C4,C5,C6 | 10 uF Capacitors  | C96446                 |
| 3        | C2,C3,C7    | 0.1 uF Capacitors | C14663                 |
| 1        | R1          | 120Ω Resistor      | C22787                 |
| 1        | R2          | 510Ω Resistor      | C23193                 |

---

## LinTool Case

Small 3D printed case to protect PCB for Lab use. There is a normal wired case and a Coaxial cable case

**NOTE** you will need 4, 2-56 screws

These .stl files can be found in [Lin_tool_cases](Lin_tool_cases) folder withing this project