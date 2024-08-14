# TODO: Do not allow DAC frequencies to be different for ssb

import numpy as np

class RfsocPulses():

    def __init__(self, imported_seqs, ch_map=None, gains={}, delays={}, iq_mix=False, print_params=False):
        """
        Constructor method.
        Creates and prints dictionary containing all specified pulse sequence 
        parameters for each channel.

        Parameters
        ----------
        imported_seqs : list
            Pulse sequences to be generated by DACs and DIG outputs.
        ch_map : dict, optional
            Map names of pulse sequences to channels on board.
        gains : dict, optional
            Specify gain of DACs in arbitrary units [0, 32765], overriding DEFAULT_GAIN.
        delays : dict, optional
            Specify delays of channels for synchronisation (+ve int), overriding DEFAULT_DELAY.
        iq_mix : bool, optional
            DAC_A lags DAC_B by 90 degrees for IQ mixing. Defaults to False.
        print_params : bool, optional
            If True, print pulse parameters. Defaults to False.
        """
        self.ch_cfg = {}
        self.iq_data = {}
        self.dig_seq = {}

        self.DEFAULT_DELAY = 0
        self.DEFAULT_GAIN = 10000

        self.map_seqs(imported_seqs, ch_map) # Map sequences to appropriate channels
        self.check_delays(delays) # Check delay dictionary is valid
        self.check_gains(gains) # Check gain dictionary is valid

        for ch, seq_params in self.pulse_seqs.items():
            self.ch_cfg[ch] = {}

            self.check_ch(ch) # Check channel string is valid
            ch_type = self.ch_cfg[ch]["ch_type"] = ch.split('_')[0]
            ch_ref = ch.split('_')[1]
            if ch_type == "DIG":
                self.ch_cfg[ch]["ch_index"] = int(ch_ref)
            elif ch_type == "DAC":
                self.ch_cfg[ch]["ch_index"] = {'A': 1, 'B': 0}.get(ch_ref)

            # Assign specified or default gains and delays for channel
            self.ch_cfg[ch]["delay"] = delays.get(ch, self.DEFAULT_DELAY)
            if ch_type == "DAC":
                self.ch_cfg[ch]["gain"] = gains.get(ch, self.DEFAULT_GAIN)
            
            # Create lists of pulse parameters
            self.ch_cfg[ch].update({"lengths":[], "times":[]})
            if ch_type ==  "DAC":
                self.ch_cfg[ch].update({"amps":[], "freqs":[], "phases":[], "styles":[], "outsels":[]})
                self.iq_data[ch] = {"idata":[], "qdata":[]}

            time = 0
            for params in seq_params:
                if isinstance(params, tuple): # Regular pulse
                    self.check_params(ch, params)
                    length_ns = params[0]

                    if bool(params[1]) == True: # A pulse exists
                        self.ch_cfg[ch]["times"].append(float(time/1e3)) # Trigger time [us]
                        self.ch_cfg[ch]["lengths"].append(float(length_ns/1e3)) # Pulse durations [us]

                        if ch_type == "DAC":
                            self.ch_cfg[ch]["amps"].append(float(params[1])) # DAC amplitude
                            self.ch_cfg[ch]["freqs"].append(np.round(float(params[2]*1e3), 6)) # DAC frequency [Hz]
                            self.ch_cfg[ch]["styles"].append('const')
                            self.ch_cfg[ch]["outsels"].append(None)
                            self.iq_data[ch]["idata"].append(None)
                            self.iq_data[ch]["qdata"].append(None)

                            # Enable simple IQ mixing
                            if iq_mix == True and ch_ref == 'B':
                                self.ch_cfg[ch]["phases"].append(float(params[3] - 90)) # DAC phase [deg]
                            else:
                                self.ch_cfg[ch]["phases"].append(float(params[3])) # DAC phase [deg]

                else: # Arb. pulse
                    length_ns = params.total_length

                    self.ch_cfg[ch]["times"].append(float(time/1e3))
                    self.ch_cfg[ch]["lengths"].append(float(length_ns/1e3))
                    self.ch_cfg[ch]["amps"].append('arb')
                    self.ch_cfg[ch]["phases"].append('arb')
                    self.ch_cfg[ch]["styles"].append('arb')
                    self.ch_cfg[ch]["outsels"].append(params.outsel)
                    self.iq_data[ch]["idata"].append(params.idata)
                    self.iq_data[ch]["qdata"].append(params.qdata)

                    if params.freq is not None:
                        self.ch_cfg[ch]["freqs"].append(np.round(float(params.freq*1e3), 6))
                    else:
                        self.ch_cfg[ch]["freqs"].append(params.outsel)

                time += length_ns
                
            self.ch_cfg[ch]["num_pulses"] = len(self.ch_cfg[ch]["lengths"]) # Number of pulses
            self.ch_cfg[ch]["duration"] = time/1e3 # End time of sequence [us]

        self.end_time = self.get_end_time()
        self.print_params(print_params)

    def map_seqs(self, imported_seqs, ch_map):
        """
        Maps imported sequences from pickle file to channels specified in dict 'ch_map'.

        Parameters
        ----------
        imported_seqs : list
            Pulse sequences to be generated by DACs and DIG outputs.
        ch_map : dict
            Map names of pulse sequences to channels on board.
        """
        if ch_map != None:
            self.pulse_seqs = {}
            for key, value in ch_map.items():
                self.pulse_seqs[key] = imported_seqs[value]
        else:
            self.pulse_seqs = imported_seqs

    def check_ch(self, ch):
        """
        Check if channel string is valid.

        Parameters
        ----------
        ch : str
            Name of generator channel.
        
        Raises
        ------
        KeyError
            Name of generator channel is not valid.
        """
        valid_chs = ["DAC_A", "DAC_B", "DIG_0", "DIG_1", "DIG_2", "DIG_3"]
        if ch not in valid_chs:
            raise KeyError(f"{ch} not a valid channel. Try:\n{valid_chs}")

    def check_gains(self, gains):
        """
        Check if dict 'gains' has keys that are valid channels, and values that
        are ints or floats with a magnitude that is not greater than 30000.

        Parameters
        ----------
        gains : dict
            DAC channel gains.
        
        Raises
        ------
        TypeError
            Gain is not an int or a float.
        ValueError
            Magnitude of gain exceeds 32765.
        """
        for ch, gain in gains.items():
            self.check_ch(ch)

            if not isinstance(gain, (int, float)):
                raise TypeError(f"{ch} gain '{gain}' is a {type(gain)}. Must be a float or int")

            if abs(gain) > 32767:
                raise ValueError(f"{ch} gain magnitude '{abs(gain)}' greater than 32766")

    def check_delays(self, delays):
        """
        Check if dict 'delays' as keys that are valid channels, and values that
        are ints.

        Parameters
        ----------
        delays : dict
            Delays to be applied to generator channels for synchronisation.
        
        Raises
        ------
        TypeError
            Specified delay is not an integer.
        """
        for ch, delay in delays.items():
            self.check_ch(ch)
            if not isinstance(delay, int):
                raise TypeError(f"{ch} delay '{delay}' not integer number of clock cycles")

    def check_params(self, ch, params):
        """
        Check if the correct number of parameters have been specified for each 
        pulse in array.

        Parameters
        ----------
        ch : str
            Name of generator channel.
        params : list
            Generator channel parameters.
        
        Raises
        ------
        IndexError
            Too many parameters specified for DAC or DIG channel.
        ValueError
            DAC amplitude must lie between 0 and 1.
        ValueError
            Parameter is not a float or an int.
        """

        if (bool(params[1]) == False) and (len(params) > 2):
            raise IndexError(f"Specified too many sequence parameters for pulse in channel {ch}")
        elif bool(params[1]) == True:
            if ((len(params) > 2) and (self.ch_cfg[ch]["ch_type"] == "DIG")
                or (len(params) > 4) and (self.ch_cfg[ch]["ch_type"] == "DAC")):
                raise IndexError(f"Specified too many sequence parameters for pulse in channel {ch}")
        
        if self.ch_cfg[ch]["ch_type"] == "DAC":
            if not 0 <= float(params[1]) <= 1.0:
                raise ValueError(f"Amplitude {float(params[1])} must be lie between 0 and 1")

        for param in params:
            if not isinstance(param, (float, int)):
                raise ValueError(f"Parameter {param} is a {type(param)}. Must be a float or int")

    def get_end_time(self):
        """
        Find time at which longest sequence ends and assign corresponding class
        variable 'end_time'.
        """
        # Find and print time at which longest sequence ends
        end_times = [self.ch_cfg[ch]["duration"] for ch in self.ch_cfg]

        if not all(i == end_times[0] for i in end_times):
            print(f"WARNING! Not all sequences are of the same duration: {end_times}")
        
        return max(end_times)
    
    def print_params(self, enabled):
        """
        Prints dictionary containing pulse parameters for each channel. Useful for debugging.

        Parameters
        ----------
        enabled : bool
            If True, print pulse parameters.
        """
        if enabled:
            for ch in self.pulse_seqs:
                if self.ch_cfg[ch]["ch_type"] == "DIG":
                    print(f"----- DIG {self.ch_cfg[ch]['ch_index']} ------")
                elif self.ch_cfg[ch]["ch_type"] == "DAC":
                    if self.ch_cfg[ch]['ch_index'] == 1:
                        print(f"----- DAC A -----")
                    elif self.ch_cfg[ch]['ch_index'] == 0:
                        print(f"----- DAC B -----")

                for key, value in self.ch_cfg[ch].items():
                    print(f"{key}: {value}")

            print(f"----- End time: {self.end_time} -----")

    def generate_asm(self, prog, calibration=None, const_power=None, reps=1):
        """
        Generate tproc assembly that produces appropriately timed pulses 
        according to parameters specified in parsed lists.

        Parameters
        ----------
        prog : class
            Instructions to be executed by tproc.
        calibration : object, optional
            RfsocCalibration object containing DAC phase alignment and SSB parameter dictionaries, by default None.
        reps : int, optional
            Number of times the pulse sequence is to be repeated. Defaults to 1.
        """
        ch_cfg = self.ch_cfg

        prog.synci(200)  # Give processor some time to configure pulses
        prog.regwi(0, 14, reps - 1) # 10 reps, stored in page 0, register 14
        prog.label("LOOP_I") # Start of internal loop

        for ch in ch_cfg:
            if ch_cfg[ch]["ch_type"] == "DAC":
                self.gen_dac_asm(prog, ch, calibration, const_power)
            elif ch_cfg[ch]["ch_type"] == "DIG":
                self.gen_dig_seq(prog, ch)

        self.gen_dig_asm(prog)

        # TODO: Investigate whether wait_all() is necessary
        # prog.wait_all() # Pause tproc until all channels finished sequences
        prog.synci(prog.us2cycles(self.end_time)) # Sync all channels when last channel finished sequence
        prog.loopnz(0, 14, "LOOP_I") # End of internal loop
        prog.end()

    def gen_dac_asm(self, prog, ch, calibration, const_power):
        """
        DAC specific assembly instructions for use in generate_asm()

        Parameters
        ----------
        prog : object
            Instructions to be executed on tproc.
        ch : str
            Name of generator channel.
        calibration : object
            RfsocCalibration object containing DAC phase alignment and SSB parameter dictionaries.
        """
        # TODO: Remove constant power

        ch_cfg = self.ch_cfg
        ch_index = ch_cfg[ch]["ch_index"]

        prog.declare_gen(ch=ch_index, nqz=1) # Initialise DAC channel

        for i in range(ch_cfg[ch]["num_pulses"]):
            time_us = ch_cfg[ch]["times"][i]
            if i > 0:
                if round(time_us, 9) > round(ch_cfg[ch]["times"][i-1] + ch_cfg[ch]["lengths"][i-1], 9):
                    time = prog.us2cycles(time_us) + ch_cfg[ch]["delay"]
                else:
                    time = "auto"
            else:
                time = prog.us2cycles(time_us) + ch_cfg[ch]["delay"]

            if ch_cfg[ch]["styles"][i] == 'const':
                freq_hz = ch_cfg[ch]["freqs"][i]
                freq = prog.freq2reg(freq_hz, gen_ch=ch_index)

                phase_deg = ch_cfg[ch]["phases"][i]
                if calibration is not None:
                    phase_deg += calibration.phase(freq_hz, ch_index)
                phase = prog.deg2reg(phase_deg, gen_ch=ch_index)

                length_us = ch_cfg[ch]["lengths"][i]
                length = prog.us2cycles(length_us, gen_ch=ch_index)

                # TODO: Temporary divide by 2 for constant amp with arb.
                if const_power is not None:
                    amp = int((const_power[freq_hz] * calibration.scale_gain(freq_hz, ch_index))/2)
                else:
                    amp = int(ch_cfg[ch]["amps"][i] * ch_cfg[ch]["gain"]/2)
                    if calibration is not None:
                        amp = int((amp*calibration.scale_gain(freq_hz, ch_index))/2)

                prog.set_pulse_registers(ch=ch_index,
                                         gain=amp,
                                         freq=freq,
                                         phase=phase,
                                         style="const",
                                         length=length
                                         )
            
            if ch_cfg[ch]["styles"][i] == 'arb':
                # TODO: Include constant power calibration
                amp = ch_cfg[ch]["gain"]
                outsel=ch_cfg[ch]["outsels"][i]

                if ch_cfg[ch]["outsels"][i] == 'product':
                    # TODO: Add phase calibration
                    freq = prog.freq2reg(ch_cfg[ch]["freqs"][i], gen_ch=ch_index)
                    phase = prog.deg2reg(0, gen_ch=ch_index)
                elif ch_cfg[ch]["outsels"][i] == 'input':
                    freq = 0
                    phase = 0

                arb_name = "arb" + str(i)
                idata = self.iq_data[ch]["idata"][i] 
                qdata = self.iq_data[ch]["qdata"][i]
                prog.add_envelope(ch=ch_index, name=arb_name, idata=idata, qdata=qdata)

                prog.set_pulse_registers(ch=ch_index,
                                         gain=amp,
                                         freq=freq,
                                         phase=phase,
                                         style="arb",
                                         waveform=arb_name,
                                         outsel=outsel
                                         )

            prog.pulse(ch=ch_index, t=time)

    def gen_dig_seq(self, prog, ch):
        """
        Create class dict 'dig_seq' containing all digital pulse parameters.

        Parameters
        ----------
        prog : object
            Instructions to be executed on tproc.
        ch : str
            Name of generator channel.
        """
        ch_cfg = self.ch_cfg
        ch_index = ch_cfg[ch]["ch_index"]

        for i in range(ch_cfg[ch]["num_pulses"]):
            # DIG pulse length 
            length = prog.us2cycles(ch_cfg[ch]["lengths"][i])

            # DIG pulse start time
            time = prog.us2cycles(ch_cfg[ch]["times"][i]) + ch_cfg[ch]["delay"]

            # Add beginning of DIG pulse
            if time in self.dig_seq:
                self.dig_seq[time].append((ch_index, True))
            else:
                self.dig_seq[time] = [(ch_index, True)]

            # Add end of DIG pulse
            if time+length in self.dig_seq:
                self.dig_seq[time+length].append((ch_index, False))
            else:
                self.dig_seq[time+length] = [(ch_index, False)]

        # Not strictly necessary but makes inspecting assembly easier
        self.dig_seq = dict(sorted(self.dig_seq.items()))

    def gen_dig_asm(self, prog):
        """
        Digital output specific assembly instructions for use in generate_asm()

        Parameters
        ----------
        prog : object
            Instructions to be executed on tproc.
        """
        soccfg = prog.soccfg

        # Program DIG after all channels have been configured
        rp, r_out = 0, 31 # tproc register page, tproc register
        dig_id = soccfg['tprocs'][0]['output_pins'][0][1]

        r_val = 0
        for time, states in self.dig_seq.items():
            for l in states:
                ch_index = l[0]
                state = l[1]

                # Set appropriate bits in register to reflect desired output state
                if state == True:
                    r_val |= (1 << ch_index)
                elif state == False:
                    r_val &= ~(1 << ch_index)

            prog.regwi(rp, r_out, r_val) # Write to register
            prog.seti(dig_id, rp, r_out, time) # Assign digital output

    def config_internal_start(self, soc, prog, load_pulses=True, reset=False):
        """
        Configure the tproc for internal triggering using the soc.tproc.start() function.

        Parameters
        ----------
        soc : object
            RFSoC object.
        prog : object
            Instructions to be executed on tproc.
        load_pulses : bool, optional
            Load pulses from program into RFSoC.
        reset : bool, optional
            Stop the tproc.
        """
        if prog.binprog is None:
            prog.compile()

        soc.start_src("internal")
        soc.stop_tproc(lazy=not reset)

        if load_pulses:
            prog.load_pulses(soc)
        prog.config_gens(soc)
        prog.config_readouts(soc)

        soc.load_bin_program(prog.binprog)

    def config_external_start(self, soc, prog, load_pulses=True, reset=False):
        """
        Configure the tproc for external triggering using PMOD1_0.

        Parameters
        ----------
        soc : object
            RFSoC object.
        prog : object
            Instructions to be executed on tproc.
        load_pulses : bool, optional
            Load pulses from program into RFSoC.
        reset : bool, optional
            Stop the tproc.
        """
        if prog.binprog is None:
            prog.compile()

        soc.start_src("external")
        soc.stop_tproc(lazy=not reset)

        if load_pulses:
            prog.load_pulses(soc)
        prog.config_gens(soc)
        prog.config_readouts(soc)

        soc.load_bin_program(prog.binprog)