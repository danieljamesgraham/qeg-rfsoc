# Quantum Engineering Group RFSoC Repository

## Useful Notebooks

Read through and run the indexed notebooks in the root directory to learn about the capabilities of the board and how to write programs for it.

## Getting Started

- Go to `http://BOARD_IP:9090/lab` in browser.
    - The default board IP is `192.168.2.99`.
    - The Jupyter Lab password is initially `xilinx`
- Run cell in `01_nameserver.ipynb`, followed by cell in `02_server.ipynb`.
- The necessary Python packages to use are board are contained in `requirements.txt`.

## Changing the Board's IP Address

- Open an SSH connection to the board.
  - The default username and password are both `xilinx`.
- Open the Ethernet network interface configuration file:

```
sudoedit /etc/network/interfaces.d/eth0
```

- Change the host ID of the IP address in line 6 (ie. change '99' in `address 192.168.2.99`) to an ID that is not currently utilised.

## Potential issue and quick fix to pulse generation with qick 0.2.394 (and above).
- Changes to the rfsoc_lib/rfsoc_pulses.py to accomodate for pulse generation errors with the line "prog.load_pulses(soc)", where one gets the following error: "AttributeError: 'QickProgram' object has no attribute 'load_pulses'".
- The solution is to run the following line, which replaces the next few lines in initializing the ADC and DAC channels, along with the start source.
```
prog.run(soc,  load_prog=True, load_envelopes=True, start_src='internal') // prog.run(soc,  load_prog=True, load_envelopes=True, start_src='external')
```