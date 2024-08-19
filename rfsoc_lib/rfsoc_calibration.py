# TODO: Raises and warnings
# print("WARNING: No phase offset has been specified")
# raise KeyError("Must include DAC calibration dac_phis for SSB")
# print(f"WARNING: pulse phase {phase_deg} is ignored for SSB")
# raise ValueError("DAC gains must be equal for SSB")

import bisect

class RfsocCalibration():
    def __init__(self, dac_phis, ssb_params=None, const_power=None, gain_factor=1):
        """
        Constructor method.
        Creates object containing DAC phase alignment and SSB parameter dictionaries.

        Parameters
        ----------
        dac_phis : dict
            Calibrated DAC phase alignment dictionary.
        ssb_params : dict, optional
            Calibrated SSB paramater dictionary, by default None.
        const_power : dict, optional
            Calibrated constant frequency-dependent ouptut power dictionary, by default None.
        gain_factor : float, optional
            Multiplicative DAC gain.
        """
        self.dac_phis = dac_phis
        self.ssb_params = ssb_params
        self.const_power = const_power
        self.gain_factor = gain_factor

        if self.const_power is None:
            self.abs_gain = False
        else:
            self.abs_gain = True
    
    def phase(self, freq, ch_index):
        """
        Provides calibrated phase for DAC phase alignment or optimal SSB.

        Parameters
        ----------
        freq : float
            Frequency for which phase should be shifted.
        ch_index : int
            DAC channel index.

        Returns
        -------
        float
            Calibrated phase [deg.].
        """
        default_phi = 0

        if ch_index == 0:
            # DAC calibration phase
            dac_phis = dict(sorted(self.dac_phis.items()))
            dac_phi = self.interpolate_param(dac_phis, freq, dac_phi=True) % 360

            # SSB calibration phase
            if self.ssb_params is None:
                ssb_phi = 0
            else:
                ssb_phis = dict(sorted(self.ssb_params["phases"].items()))
                ssb_phi = self.interpolate_param(ssb_phis, freq) % 360
            
            # Sum phases
            phi = (dac_phi + ssb_phi) % 360

            return phi
        
        if ch_index == 1:
            return default_phi
    
    def scale_gain(self, freq, ch_index):
        """
        Scales DAC channel gains for optimal SSB.

        Parameters
        ----------
        freq : float
            Frequency for which gain should be scaled.
        ch_index : int
            DAC channel index

        Returns
        -------
        float
            Gain scale factor.
        """
        if self.ssb_params is None:
            return self.gain_factor
        
        else:
            ssb_gains = dict(sorted(self.ssb_params["gains"].items()))
            if ch_index == 0:
                return self.gain_factor
            
            if ch_index == 1:
                ssb_gain = self.interpolate_param(ssb_gains, freq)
                scale_gain = ssb_gain * self.gain_factor / self.ssb_params["default_gain"]
                return scale_gain
    
    def gain(self, freq, ch_index):
        """
        Provides absolute gain (may be scaled by gain_factor) for power-calibrated SSB.

        Parameters
        ----------
        freq : float
            Pulse frequency.
        ch_index : int
            DAC channel index.

        Returns
        -------
        int
            Absolute gain for power-calibrated SSB.

        Raises
        ------
        ValueError
            const_power not specified when initialising calibration object.
        """

        if self.const_power is None:
            raise ValueError("Cannot return absolute gain as const_power not specified when initialising calibraiton object")
        
        gain = int(self.const_power[freq] * self.scale_gain(freq, ch_index))

        return gain
    
    def interpolate_param(self, param_dict, freq, dac_phi=False):
        """
        Interpolate between frequencies in parameter dictionaries.

        Parameters
        ----------
        param_dict : dict
            Dictionary containing frequencies as keys and parameters as values.
        freq : float
            Frequency for which parameters are interpolated
        dac_phi : bool, optional
            For DAC calibration to mitigate errors from sliding phase, by default False

        Returns
        -------
        float
            Interpolated value.
        """
        i = bisect.bisect_left(list(param_dict.keys()), freq)
        freq_above = list(param_dict.keys())[i]
        val_above = param_dict[list(param_dict.keys())[i]]
        freq_below = list(param_dict.keys())[i-1]
        val_below = param_dict[list(param_dict.keys())[i-1]]

        if dac_phi == True:
            if abs(val_above - val_below) > 330:
                if val_above > val_below:
                    val_below += 360
                elif val_above < val_below:
                    val_above += 360

        val = (val_below + (((freq - freq_below) / (freq_above - freq_below)) * (val_above - val_below)))
 
        return val 