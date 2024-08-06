import bisect

class RfsocCalibration():
    def __init__(self, dac_phis, ssb_params=None):
        self.dac_phis = dac_phis
        self.ssb_params = ssb_params

        self.DEFAULT_PHI = 0
        self.DEFAULT_GAIN_FACTOR = 1
    
    def phase(self, freq, ch_index, iq_mix=False):
        if ch_index == 0:
            # DAC calibration phase
            dac_phis = dict(sorted(self.dac_phis.items()))
            dac_phi = self.interpolate(dac_phis, freq, dac_phi=True) % 360

            # SSB calibration phase
            if self.ssb_params is None:
                ssb_phi = 0
            else:
                ssb_phis = dict(sorted(self.ssb_params["phases"].items()))
                ssb_phi = self.interpolate(ssb_phis, freq) % 360
            
            # Sum phases
            phi = (dac_phi + ssb_phi - iq_mix*90) % 360

            return phi
        
        if ch_index == 1:
            return self.DEFAULT_PHI
    
    def scale_gain(self, freq, ch_index):
        if self.ssb_params is None:
            return self.DEFAULT_GAIN_FACTOR
        
        else:
            ssb_gains = dict(sorted(self.ssb_params["gains"].items()))
            if ch_index == 0:
                return self.DEFAULT_GAIN_FACTOR
            
            if ch_index == 1:
                ssb_gain = self.interpolate(ssb_gains, freq)
                gain_factor = ssb_gain / self.ssb_params["default_gain"]
                return gain_factor
    
    def interpolate(self, vals, freq, dac_phi=False):
        ind = bisect.bisect_left(list(vals.keys()), freq)

        freq_above    = list(vals.keys())[ind]
        val_above = vals[list(vals.keys())[ind]]
        # print(freq_above, val_above)
        freq_below    = list(vals.keys())[ind-1]
        val_below = vals[list(vals.keys())[ind-1]]
        # print(freq_below, val_below)

        if dac_phi == True:
            if abs(val_above - val_below) > 330:
                if val_above > val_below:
                    val_below += 360
                elif val_above < val_below:
                    val_above += 360


        val = (val_below + (((freq - freq_below) / (freq_above - freq_below)) * (val_above - val_below)))

        # print(val)
 
        return val 


                # print("WARNING: No phase offset has been specified")

                # raise KeyError("Must include DAC calibration dac_phis for SSB")

                    # print(f"WARNING: pulse phase {phase_deg} is ignored for SSB")

        # if (ssb_params is not None) and (ch_cfg["DAC_A"]["gain"] != ch_cfg["DAC_B"]["gain"]):
        #     raise ValueError("DAC gains must be equal for SSB")
