import numpy as np

class RfsocArbPulses():
    def __init__(self, soccfg, sequence, outsel):
        """
        Constructor method.
        Initialise RfsocArbPulses object by creating IQ data samples for DAC.
        Provide total sequence length, frequency, and outsel mode for RfsocPulses object.

        Parameters
        ----------
        soccfg : object
            RFSoC board object.
        sequence : list
            List of tuples providing pulse sequence parameters in form [(time, amp, freq, phase), ...].
        outsel : str
            DAC outsel mode. Use 'product' to provide IQ amplitude envelope and 'input' to produce arbitrary DAC samples.

        Raises
        ------
        TypeError
            Outsel must be either 'product' or 'input'.
        ValueError
            Frequency is fixed to that of the first pulse when outsel='product'.
        ValueError
            Amplitude must lie between 0 and 1.
        RuntimeError
            Number of IQ samples exceeds the maximum of 65536.
        """
        gain = 32766
        fs_dac = soccfg['gens'][0]['fs'] # 9830.4 MHz

        if outsel == 'product':
            self.freq = sequence[0][2] # Frequency is fixed at the first value
        elif outsel == 'input':
            self.freq = None
        else:
            raise TypeError(f"Outsel {outsel} must be 'product' or 'input'")

        total_length = 0
        actual_times = []
        idata, qdata = np.array([]), np.array([])
        for params in sequence:
            # Extract pulse parameters
            amp = params[1]
            length = params[0]
            total_length += length

            # Calculate number of DAC sampling cycles and actual pulse time
            cycles = int(np.round((length) * fs_dac / 1e3, 0))
            actual_times.append(cycles * 1e3 / fs_dac)

            if 0 < amp <= 1: # Producing output
                if outsel == 'product':
                    # Calculate amp_i and amp_q from phase and gain
                    # TODO: Add phase calibration
                    phi = params[3]
                    dac_iq = np.round(np.e**(1j * phi * np.pi / 180), 10)
                    dac_i, dac_q = np.real(dac_iq), np.imag(dac_iq)
                    amp_i = int(gain * amp * dac_i)
                    amp_q = int(gain * amp * dac_q)

                    if params[2] != self.freq:
                        raise ValueError(f"Cannot specify frequency {params[2]} GHz as frequency is fixed to that of first pulse ({self.freq} GHz)")

                    # Concatenate appropriate number of amp_i and amp_q to idata and qdata
                    idata = np.concatenate((idata, np.full(shape=cycles, fill_value=amp_i, dtype=int)))
                    qdata = np.concatenate((qdata, np.full(shape=cycles, fill_value=amp_q, dtype=int)))

                if outsel == 'input':
                    # TODO: Add phase calibration
                    freq = params[2] * 1e3
                    phi = params[3]

                    # Concatenate specified sinusoid to idata and qdata
                    ts = np.arange(0, cycles, 1) / fs_dac
                    y = amp * gain * np.sin(2*np.pi*freq*ts + (np.pi*phi)/180) / 2
                    idata = np.concatenate((idata, -np.array(y)))
                    qdata = np.concatenate((qdata, np.zeros(cycles, dtype=int)))

            elif amp == 0: # Not producing output
                # Concatenate appropriate number of zeros to idata and qdata
                idata = np.concatenate((idata, np.zeros(cycles, dtype=int)))
                qdata = np.concatenate((qdata, np.zeros(cycles, dtype=int)))

            else:
                raise ValueError(f"Amplitude {amp} must lie between 0 and 1")

        # Pad data so that array lengths are multiples of 16
        padding = 16 - (len(idata) % 16)
        idata = np.pad(idata,
                    pad_width = (0, padding),
                    mode = 'constant',
                    constant_values = 0)
        qdata = np.pad(qdata,
                    pad_width = (0, padding),
                    mode = 'constant',
                    constant_values = 0)
        
        if len(idata) > 65536:
            raise RuntimeError(f"IQ buffer length is {len(idata)} samples ({round(len(idata)/fs_dac, 2)} us)\nIt must be 65536 samples ({round(65536/fs_dac, 2)} us) or less")

        # TODO: Provide 'actual' times of pulses
        # actual_total_length = len(idata) * 1e3 / fs_dac # us
        # self.actual_times = actual_times
        # self.actual_total_length = actual_total_length
 
        self.idata = idata
        self.qdata = qdata
        self.total_length = total_length
        self.outsel = outsel