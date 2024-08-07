# TODO: print("WARNING: No phase offset has been specified")
# TODO: raise KeyError("Must include DAC calibration dac_phis for SSB")
# TODO: print(f"WARNING: pulse phase {phase_deg} is ignored for SSB")
# TODO: raise ValueError("DAC gains must be equal for SSB")

import bisect

class RfsocCalibration():
    def __init__(self, dac_phis, ssb_params=None):
        """
        Constructor method.
        Creates object containing DAC phase alignment and SSB parameter dictionaries.

        Parameters
        ----------
        dac_phis : dict
            Calibrated DAC phase alignment dictionary.
        ssb_params : dict, optional
            Calibrated SSB paramater dictionary, by default None.
        """
        self.dac_phis = dac_phis
        self.ssb_params = ssb_params

        self.DEFAULT_PHI = 0
        self.DEFAULT_GAIN_FACTOR = 1
    
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
            return self.DEFAULT_PHI
    
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
            return self.DEFAULT_GAIN_FACTOR
        
        else:
            ssb_gains = dict(sorted(self.ssb_params["gains"].items()))
            if ch_index == 0:
                return self.DEFAULT_GAIN_FACTOR
            
            if ch_index == 1:
                ssb_gain = self.interpolate_param(ssb_gains, freq)
                gain_factor = ssb_gain / self.ssb_params["default_gain"]
                return gain_factor
    
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