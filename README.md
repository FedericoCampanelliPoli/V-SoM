# V-SoM 
## Versatile-System on Module Board for control applications
V-SoM is an embeddable System on Module (SoM) for converter control applications that can be programmed with PLECS, Simulink or C. Targeting microcontroller-based control modules for power electronics converters and custom embedded applications. 

<img width="454" height="343" alt="immagine" src="https://github.com/user-attachments/assets/1e4d6177-b11d-4a40-bb3b-c211c3917550" /> 

### VScope2.0
Thanks to its integrated Virtual Oscilloscope, the PC can view, edit and store data in real time running on the controller up to 50kSPS and 60 channels.

<img width="1920" height="1032" alt="Screenshot 2026-01-26 135236" src="https://github.com/user-attachments/assets/c56da395-f914-4491-8722-93953c0aaad4" />

_Three phase sinewave computed on the microcontroller and streamed in real time to VScope2.0_

The architecture relies on a dual core H755 microcontroller by ST-Microelectronics, running on a 32-bit ARM® Cortex®-M7, implementing an ethernet server to connect to a Python14 based control platform on the remote computer. The control algorithm can run on the industry standard 32-bit Arm® Cortex®-M4 core, left free to the user to implement custom power electronics algorithms. It is ideally suited for fast prototyping, and medium volume production scales; seamlessly allowing the user to transition to industry proven platforms relying on 32-bit Arm® Cortex®-M4 cores, such as the STM F4, STM G4, STM L4 microcontrollers for mass production.

The SoM allows the user to easily integrate and validate controls with the hardware development of power converters, such as grid-tied inverters, motor drives, isolated DCDCs, plus any kind of embedded application requiring custom embedded controllers, thanks to: 

<img width="643" height="182" alt="immagine" src="https://github.com/user-attachments/assets/fe649a88-a952-4d06-8024-fe6021a57841" />

Coming in a pre-programmed state, the control can be seamlessly tested in the favorite software environment (PLECS, Simulink, Simscape, others) and directly programmed in the microcontroller thanks to embedded coder environments, or hard coded on bare metal using C on CubeIDE or STM addons to VSCode.

The SoM coming on a 4.5x5.2cm six-layer high speed PCB, which includes a STDC14 connector for the programmer and a 100Mbit/s Ethernet PHY, can be soldered on any traditional PCB thanks to its castellation connector, and access the data in its oscilloscope like app, to monitor the status, the measurements and setpoints of the converter. The Ethernet RJ45 connector with built-in magnetics already provides galvanic isolation, to avoid circulation of EMI interferences among computers or other converters, while the two integrated LDOs already provide the 3.3V to the user, from a supply of 3.3-5.5V as input. 

Two user LEDs and one power LED indicate the running status of the board.
Simplifying the converter control peripheral and coding implementation and real time debug thanks to its high compatibility with STM 144-Nucleo boards for parallel embedded development, allowing the user to focus on control algorithms and power PCB layout, without sacrificing cost, space and performance.

> [!NOTE]
> Comparison is only qualitative

<img width="1004" height="493" alt="immagine" src="https://github.com/user-attachments/assets/3ea0d0b6-41a3-44fb-9fcb-a297f40477f4" />

The acquired data can be stored in .csv file and as a scope acquisition, like a modern oscilloscope, thus enabling the user to review the acquired data and perform post processing operations. The “Options” tab allows to name the channels according to the stored variable, the subscript _r protects a variable from being overwritten in software.

> [!WARNING]
> Windows Firewall might block the UDP communications from arriving, in that case a firewall rule must be added as:
> 
`netsh advfirewall firewall add rule name="VScope UDP 5005" dir=in action=allow protocol=UDP localport=5005`

https://github.com/user-attachments/assets/e4af8ac9-157b-435e-b1ee-e60cd0c03de7

Thanks to Simulink embedded coder it is possible to generate an executable c-code application on the target microcontroller, allowing the development of rapid prototyping workflows for power converter and electric drives control strategies. Thanks to the free embedded C environment it is possible to write manually the control logic, freeing the user from proprietary softwares. 

<img width="500" height="300" alt="immagine" src="https://github.com/user-attachments/assets/9532c526-04c9-43f0-8f12-ae2f5f331176" /> <img width="500" height="300" alt="immagine" src="https://github.com/user-attachments/assets/7bee993a-cacd-4d28-90b1-c374fef0e6a8" />






