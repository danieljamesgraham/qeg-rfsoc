# Quantum Engineering Group RFSoC Repository

## Useful Notebooks

- Notebook `00_dac_phase_calibration.ipynb` is used to calibrate the phase offset between DACs.
- Notebook `01_rfsoc_pulses_demo.ipynb` is a short demo notebook.
- Notebook `02_rfsoc_limitations.ipynb` outlines the limitations of the RFSoC 4x2 board.

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

Note that frequency is fixed to first value for outsel='product'