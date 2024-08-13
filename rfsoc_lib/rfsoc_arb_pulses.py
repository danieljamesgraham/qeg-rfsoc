import numpy as np

class RfsocArbPulses():
    def __init__(self, sequence, mode='iq'):
        idata, qdata = np.array([]), np.array([])
        actual_times = []
        total_time = 0

        # fs_dac = prog.soccfg['gens'][0]['fs']
        fs_dac = 9830.4
        gain = 32766

        if mode == 'iq':
            self.outsel = 'product'
            # TODO: Warn that frequency is fixed
            self.freq = sequence[0][2]
        elif mode == 'arb':
            self.outsel = 'input'
            self.freq = 'arb'
        else:
            raise TypeError(f"Mode {mode} must be 'iq' or 'arb'")

        for params in sequence:
            # Extract pulse parameters
            length = params[0]
            amp = params[1]

            total_time += length

            # Calculate number of DAC sampling cycles and actual pulse time
            cycles = int(np.round((length) * fs_dac / 1e3, 0))
            actual_times.append(cycles * 1e3 / fs_dac)

            if 0 < amp <= 1: # Producing output
                if mode == 'iq':
                    # Calculate amp_i and amp_q from phase and gain
                    phi = params[3]
                    dac_iq = np.round(np.e**(1j * phi * np.pi / 180), 10)
                    dac_i, dac_q = np.real(dac_iq), np.imag(dac_iq)
                    amp_i = int(gain * dac_i)
                    amp_q = int(gain * dac_q)

                    # Append appropriate number of amp_i and amp_q to idata and qdata
                    idata = np.concatenate((idata, np.full(shape=cycles, fill_value=amp_i, dtype=int)))
                    qdata = np.concatenate((qdata, np.full(shape=cycles, fill_value=amp_q, dtype=int)))
                if mode == 'arb':
                    freq = params[2] * 1e3
                    phi = params[3]

                    sinusoid = []
                    for i in range(cycles):
                        x = i / fs_dac
                        sinusoid.append(amp * gain * np.sin(2*np.pi*freq*x + (np.pi*phi)/180))
                    idata = np.concatenate((idata, -np.array(sinusoid)))
                    qdata = np.concatenate((qdata, np.zeros(cycles, dtype=int)))
            elif amp == 0: # Not producing output
                # Append appropriate number of zeros to idata and qdata
                idata = np.concatenate((idata, np.zeros(cycles, dtype=int)))
                qdata = np.concatenate((qdata, np.zeros(cycles, dtype=int)))
            elif (amp < 0) or (amp > 1):
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

        # Calculate time that sequence occupies DAC
        actual_total_time = len(idata) * 1e3 / fs_dac # us
 
        self.idata = idata
        self.qdata = qdata
        self.total_time = total_time
        self.actual_times = actual_times
        self.actual_total_time = actual_total_time
        self.mode = mode