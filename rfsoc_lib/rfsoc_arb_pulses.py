# raise ValueError("Must specify frequency as an argument")
# print("WARNING: frequency has been specified as an argument but is ignored for outsel='input' pulses")
# raise TypeError(f"Outsel {outsel} must be 'product' or 'input'")

import numpy as np
import math

class RfsocArbPulses():
    def __init__(self, soccfg, sequence=None, samples=None, calibration=None, ch_index=None, outsel='product'):
        """
        Constructor method.
        Initialise RfsocArbPulses object by creating IQ data samples for DAC.
        Provide total sequence length, frequency, and outsel mode for RfsocPulses object.

        Parameters
        ----------
        soccfg : object
            RFSoC board object.
        sequence : list, optional
            List of tuples providing pulse sequence parameters in form [(time, amp, freq, phase), ...].
        samples : list, optional
            List of amplitudes to be sampled by the DAC in form [(i_sample_0, i_sample_1, ...), (q_sample_0, q_sample_1, ...)]
        calibration : object, optional
            Multi-DAC IQ mixing calibration object.
        ch_index : int, optional
            DAC channel index (for obtaining calibrated amplitude and phase).
        outsel : str, optional
            DAC outsel mode. Use 'product' to provide IQ amplitude envelope and 'input' to produce arbitrary DAC samples. 'product' by default.

        Raises
        ------
        ValueError
            Frequency must be specified as an argument when raw IQ samples are being used with outsel='product'.
        TypeError
            Outsel must be either 'product' or 'input'.
        RuntimeError
            Maxmimum number of IQ samples (65536) exceeded.
        """
        self.outsel = outsel
        self.fs_dac = soccfg['gens'][0]['fs'] # 9830.4 MHz

        # Assign frequency
        if (sequence is not None) and (outsel == 'product'):
            self.freq = sequence[0][2] # Frequency is fixed at the first value
        else:
            self.freq = 0

        # Generate IQ data
        if (sequence is None) and (samples is None):
            raise ValueError("Must specify a pulse sequence or DAC samples")
        elif (sequence is not None) and (samples is not None):
            raise ValueError("May not simultaneously specify a pulse sequence and DAC samples")
        elif sequence is not None:
            idata, qdata = self.gen_sequence_iqdata(sequence, calibration, ch_index, outsel)
        elif samples is not None:
            idata, qdata = self.gen_samples_iqdata(samples, outsel)

        # NOTE: Is this needed? Uncomment if program breaks
        # if self.total_length < soccfg.cycles2us(3, gen_ch=0) * 1e3:
        #     # Could make more precise (4.88) but 5 is nicer for user
        #     self.total_length = 5

        idata, qdata = self.pad_iqdata(idata, qdata)

        if len(idata) > 65536:
            raise RuntimeError(f"IQ buffer length is {len(idata)} samples ({round(len(idata)/self.fs_dac, 2)} us)\nIt must be 65536 samples ({round(65536/self.fs_dac, 2)} us) or less")

        # # Provide 'actual' times of pulses
        # actual_total_length = len(idata) * 1e3 / self.fs_dac # us
        # self.actual_times = actual_times
        # self.actual_total_length = actual_total_length
 
        self.idata = idata
        self.qdata = qdata
    
    def gen_sequence_iqdata(self, sequence, calibration, ch_index, outsel):
        """
        Generate IQ samples from a list of tuples.

        Parameters
        ----------
        sequence : list
            List of tuples containing pulse parameters.
        calibration : object, optional
            Multi-DAC IQ mixing calibration object.
        ch_index : int, optional
            DAC channel index (for obtaining calibrated amplitude and phase).
        outsel : str
            DAC outsel mode.

        Returns
        -------
        list, list
            I, Q data.

        Raises
        ------
        ValueError
            Frequency is only taken from the first pulse.
        ValueError
            Amplitude of pulses must lie between 0 and 1.
        """
        gain = 32766

        idata, qdata = np.array([]), np.array([])
        total_length = 0
        actual_times = []
        for params in sequence:
            # Extract pulse parameters
            amp = params[1]
            length = params[0]

            total_length += length

            # Calculate number of DAC sampling cycles and actual pulse time
            cycles = int(np.round((length) * self.fs_dac / 1e3, 0))
            actual_times.append(cycles * 1e3 / self.fs_dac)

            if 0 < amp <= 1: # Producing output
                if outsel == 'product':
                    freq = self.freq * 1e3
                    # Calculate amp_i and amp_q from phase and gain
                    if calibration is None:
                        phi = params[3]
                    else:
                        phi = params[3] + calibration.phase(freq, ch_index)

                    dac_iq = np.round(np.e**(1j * phi * np.pi / 180), 10)
                    dac_i, dac_q = np.real(dac_iq), np.imag(dac_iq)

                    if calibration is None:
                        amp_i = int(gain * amp * dac_i)
                        amp_q = int(gain * amp * dac_q)
                    elif calibration.abs_gain:
                        amp_i = int(2 * dac_i * calibration.gain(freq, ch_index))
                        amp_q = int(2 * dac_q * calibration.gain(freq, ch_index))
                    else:
                        amp_i = int(gain * amp * dac_i * calibration.scale_gain(freq, ch_index))
                        amp_q = int(gain * amp * dac_q * calibration.scale_gain(freq, ch_index))

                    if (params[2] != self.freq) and (calibration is not None):
                        raise ValueError(f"Cannot specify frequency {params[2]} GHz as frequency is fixed to that of first pulse ({self.freq} GHz)")

                    # Concatenate appropriate number of amp_i and amp_q to idata and qdata
                    idata = np.concatenate((idata, np.full(shape=cycles, fill_value=amp_i, dtype=int)))
                    qdata = np.concatenate((qdata, np.full(shape=cycles, fill_value=amp_q, dtype=int)))

                if outsel == 'input':
                    # NOTE: Phase calibration is not needed in principle but phases
                    # are not aligned due to DAC jitter
                    freq = params[2] * 1e3
                    phi = params[3]

                    # Concatenate specified sinusoid to idata and qdata
                    ts = np.arange(0, cycles, 1) / self.fs_dac
                    y = np.sin(2*np.pi*freq*ts + (np.pi*phi)/180) / 2

                    if calibration is None:
                        amp_i = y * amp * gain
                    elif calibration.abs_gain:
                        amp_i = 2 * y * calibration.gain(freq, ch_index)
                    else:
                        amp_i = y * amp * gain * calibration.scale_gain(freq, ch_index)
                    
                    idata = np.concatenate((idata, -np.array(amp_i)))
                    qdata = np.concatenate((qdata, np.zeros(cycles, dtype=int)))

            elif amp == 0: # Not producing output
                # Concatenate appropriate number of zeros to idata and qdata
                idata = np.concatenate((idata, np.zeros(cycles, dtype=int)))
                qdata = np.concatenate((qdata, np.zeros(cycles, dtype=int)))

            else:
                raise ValueError(f"Amplitude {amp} must lie between 0 and 1")
            
            self.total_length = total_length
        
        return idata, qdata

    def gen_samples_iqdata(self, samples, outsel):
        """
        Generate I and Q samples from raw input array.

        Parameters
        ----------
        samples : list
            Raw I and Q samples.
        outsel : str
            DAC outsel mode.

        Returns
        -------
        list, list
            I, Q data.
        
        Raises
        ------
        ValueError
            Magnitude of IQ samples may not exceed 32566.
        """
        idata = np.array(samples[0])

        if outsel == 'product':
            qdata = np.array(samples[1])
        if (outsel == 'input'):
            qdata = np.zeros(len(idata), dtype=int)
            try:
                qlen = len(samples[1])
            except IndexError:
                qlen = 0
            if qlen > 0:
                print("WARNING: Q samples have been specified but are not utilised for outsel='input' pulses")
        
        if (abs(np.max(idata)) > 32566) or (abs(np.max(qdata) > 32566)):
            raise ValueError("IQ samples may not exceed 32566")

        self.total_length = math.ceil(len(idata) * 1e3 / self.fs_dac)
        
        return idata, qdata

    def pad_iqdata(self, idata, qdata):
        """
        Pad arrays of I and Q samples so that they have a length of at least 48 that is a multiple of 16.

        Parameters
        ----------
        idata : list
            I data.
        qdata : list
            Q data.

        Returns
        -------
        list, list
            I, Q data.
        """
        # Pad data so that array lengths are multiples of 16
        if len(idata) < 48:
            pad = 48 - len(idata)
        else:
            pad = 16 - (len(idata) % 16)
        idata = np.pad(idata,
                    pad_width = (0, pad),
                    mode = 'constant',
                    constant_values = 0)
        qdata = np.pad(qdata,
                    pad_width = (0, pad),
                    mode = 'constant',
                    constant_values = 0)
        
        return idata, qdata