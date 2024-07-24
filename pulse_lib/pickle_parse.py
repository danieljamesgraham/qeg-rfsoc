# TODO: Convert all user-input parameters into specific data-type
# TODO: Add alternative if delta_phis not specified

DEFAULT_DELAY = 0
DEFAULT_GAIN = 10000

class PickleParse():

    def __init__(self, imported_seqs, ch_map=None, gains={}, delays={}):
        """
        Constructor method.
        Creates and prints dictionary containing all specified pulse sequence 
        parameters for each channel.
        """
        self.ch_cfg = {}
        self.dig_seq = {}

        self.map_seqs(imported_seqs, ch_map) # Map sequences to appropriate channels
        self.check_delays(delays) # Check delay dictionary is valid
        self.check_gains(gains) # Check gain dictionary is valid

        for ch, seq_params in self.pulse_seqs.items():
            self.ch_cfg[ch] = {}

            self.check_ch(ch) # Check channel string is valid
            ch_type = self.ch_cfg[ch]["ch_type"] = ch.split('_')[0]
            ch_ref = ch.split('_')[1]
            if ch_type == "DIG":
                print(f"----- DIG {ch_ref} ------")
                self.ch_cfg[ch]["ch_index"] = int(ch_ref)
            elif ch_type == "DAC":
                print(f"----- DAC {ch_ref} -----")
                self.ch_cfg[ch]["ch_index"] = {'A': 1, 'B': 0}.get(ch_ref)

            # Assign specified or default gains and delays for channel
            self.ch_cfg[ch]["delay"] = delays.get(ch, DEFAULT_DELAY)
            if ch_type == "DAC":
                self.ch_cfg[ch]["gain"] = gains.get(ch, DEFAULT_GAIN)
            
            # Create lists of pulse parameters
            self.ch_cfg[ch]["lengths"] = []
            self.ch_cfg[ch]["times"] = []
            if ch_type ==  "DAC":
                self.ch_cfg[ch]["amps"] = []
                self.ch_cfg[ch]["freqs"] = []
                self.ch_cfg[ch]["phases"] = []

            time = 0
            for params in seq_params:
                self.check_params(ch, params)
                if bool(params[1]) == True:
                    self.ch_cfg[ch]["times"].append(time/1e3) # Trigger time [us]
                    self.ch_cfg[ch]["lengths"].append(params[0]/1e3) # Pulse durations [us]
                    if ch_type == "DAC":
                        self.ch_cfg[ch]["amps"].append(params[1]) # DAC amplitude
                        self.ch_cfg[ch]["freqs"].append(params[2]*1e3) # DAC frequency [Hz]
                        self.ch_cfg[ch]["phases"].append(params[3]) # DAC phase [deg]
                time += params[0]

            self.ch_cfg[ch]["num_pulses"] = len(self.ch_cfg[ch]["lengths"]) # Number of pulses
            self.ch_cfg[ch]["duration"] = time/1e3 # End time of sequence [us]

            self.check_lengths(ch) # Check that lengths of pulse parameter lists match

            for key, value in self.ch_cfg[ch].items():
                print(f"{key}: {value}")

        self.get_end_time()

    def map_seqs(self, imported_seqs, ch_map):
        """
        Maps imported sequences from pickle file to channels specified in dict 'ch_map'.
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
        """
        valid_chs = ["DAC_A", "DAC_B", "DIG_0", "DIG_1", "DIG_2", "DIG_3"]
        if ch not in valid_chs:
            raise KeyError(f"{ch} not a valid channel. Try:\n{valid_chs}")

    def check_gains(self, gains):
        """
        Check if dict 'gains' has keys that are valid channels, and values that
        are ints or floats with a magnitude that is not greater than 30000.
        """
        for ch, gain in gains.items():
            self.check_ch(ch)

            if not isinstance(gain, (int, float)):
                raise TypeError(f"{ch} gain '{gain}' not int or float")

            if abs(gain) > 32767:
                raise ValueError(f"{ch} gain magnitude '{abs(gain)}' greater than 30000")

    def check_delays(self, delays):
        """
        Check if dict 'delays' as keys that are valid channels, and values that
        are ints.
        """
        for ch, delay in delays.items():
            self.check_ch(ch)
            if not isinstance(delay, int):
                raise TypeError(f"{ch} delay '{delay}' not integer number of clock cycles")

    def check_params(self, ch, params):
        """
        Check if the correct number of parameters have been specified for each 
        pulse in array.
        """

        # TODO: Times, amps, frequencies and phases must be floats or ints
        # TODO: Make sure to raise error if too many parameters specified for DIG
        # TODO: times : float/int, +ve
        # TODO: lengths: float/int, [Currently in us but need to veryify that it is greater than 3 clock cycles]
        # TODO: amps : float/int, 0 < amp < 1
        # TODO: freqs : float/int, 0 < freq < 10 [GHz]
        # TODO: phases : float/int

        if (bool(params[1]) == False) and (len(params) > 2):
            raise Exception(f"Specified too many sequence parameters for pulse in channel {ch}")
        elif bool(params[1]) == True:
            if ((len(params) > 2) and (self.ch_cfg[ch]["ch_type"] == "DIG")
                or (len(params) > 4) and (self.ch_cfg[ch]["ch_type"] == "DAC")):
                raise Exception(f"Specified too many sequence parameters for pulse in channel {ch}")

    def check_lengths(self, ch):
        """
        Check pulse parameter lists are equal in length.
        """

        # TODO: include lengths, times, amps, freqs, phases in check

        times = self.ch_cfg[ch]["times"]
        num_pulses = self.ch_cfg[ch]["num_pulses"]
        if ((len(times) != num_pulses) or
            ((self.ch_cfg[ch]["ch_type"] == "DAC") and (len(self.ch_cfg[ch]["freqs"]) != num_pulses))):
            raise Exception("Number of elements in pulse parameter lists are not equal")

    def get_end_time(self):
        """
        Find time at which longest sequence ends and assign corresponding class
        variable 'end_time'.

        end_time : float
        """
        # Find and print time at which longest sequence ends
        end_times = [self.ch_cfg[ch]["duration"] for ch in self.ch_cfg]
        self.end_time = max(end_times)

        print(f"----- End time: {self.end_time} -----")
        if not all(i == end_times[0] for i in end_times):
            print("WARNING! Not all sequences are of the same duration")

    def generate_asm(self, prog, delta_phis={}, reps=1):
        """
        Generate tproc assembly that produces appropriately timed pulses 
        according to parameters specified in parsed lists.
        """
        ch_cfg = self.ch_cfg

        prog.synci(200)  # Give processor some time to configure pulses
        prog.regwi(0, 14, reps - 1) # 10 reps, stored in page 0, register 14
        prog.label("LOOP_I") # Start of internal loop

        for ch in ch_cfg:
            if ch_cfg[ch]["ch_type"] == "DAC":
                self.gen_dac_asm(prog, ch, delta_phis)
            elif ch_cfg[ch]["ch_type"] == "DIG":
                self.gen_dig_seq(prog, ch)

        self.gen_dig_asm(prog)

        # TODO: Are wait_all() and synci() both strictly necessary?
        prog.wait_all() # Pause tproc until all channels finished sequences
        prog.synci(prog.us2cycles(self.end_time)) # Sync all channels when last channel finished sequence
        prog.loopnz(0, 14, "LOOP_I") # End of internal loop
        prog.end()

    def gen_dac_asm(self, prog, ch, delta_phis):
        """
        DAC specific assembly instructions for use in generate_asm()
        """
        ch_cfg = self.ch_cfg
        ch_index = ch_cfg[ch]["ch_index"]

        prog.declare_gen(ch=ch_index, nqz=1) # Initialise DAC channel

        for i in range(ch_cfg[ch]["num_pulses"]):
            # DAC pulse parameters
            time = prog.us2cycles(ch_cfg[ch]["times"][i]) + ch_cfg[ch]["delay"]
            length = prog.us2cycles(ch_cfg[ch]["lengths"][i], gen_ch=ch_index)
            amp = int(ch_cfg[ch]["amps"][i] * ch_cfg[ch]["gain"])
            freq = prog.freq2reg(ch_cfg[ch]["freqs"][i], gen_ch=ch_index)
            # phase = prog.deg2reg(ch_cfg[ch]["phases"][i], gen_ch=ch_index)
            phase = prog.deg2reg(delta_phis[ch_cfg[ch]["freqs"][i]][ch_index] 
                                 + ch_cfg[ch]["phases"][i], gen_ch=ch_index)

            # Program DAC channel with parameters and then play pulse
            prog.set_pulse_registers(ch=ch_index, gain=amp, freq=freq, phase=phase,
                                     style="const", length=length)
            prog.pulse(ch=ch_index, t=time)

    def gen_dig_seq(self, prog, ch):
        """
        Create class dict 'dig_seq' containing all digital pulse parameters.

        dig_seq : dict
            key == time : int
                Time of event occurrence [clock cycles]
            val == states : list
                List of tuples in form
                [('digital channel index' : int, 'logic state' : bool), ...]
        """
        ch_cfg = self.ch_cfg
        ch_index = ch_cfg[ch]["ch_index"]

        for i in range(ch_cfg[ch]["num_pulses"]):
            # DIG pulse parameters
            time = prog.us2cycles(ch_cfg[ch]["times"][i]) + ch_cfg[ch]["delay"]
            length = prog.us2cycles(ch_cfg[ch]["lengths"][i])

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