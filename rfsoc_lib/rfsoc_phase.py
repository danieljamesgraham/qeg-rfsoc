import bisect

class RFSoCPhase():
    def __init__(self, delta_phis):
        self.delta_phis = delta_phis
    
    def phase(self, freq, ch):
        if ch == 0:
            delta_phis = dict(sorted(self.delta_phis.items()))

            ind = bisect.bisect_left(list(self.delta_phis.keys()), freq)

            freq_above      = list(self.delta_phis.keys())[ind]
            delta_phi_above = self.delta_phis[list(self.delta_phis.keys())[ind]][0]
            freq_below      = list(self.delta_phis.keys())[ind-1]
            delta_phi_below = self.delta_phis[list(self.delta_phis.keys())[ind-1]][0]

            if abs(delta_phi_above - delta_phi_below) > 330:
                if delta_phi_above > delta_phi_below:
                    delta_phi_below += 360
                elif delta_phi_above < delta_phi_below:
                    delta_phi_above += 360

            delta_phi = (delta_phi_below + (((freq - freq_below) / (freq_above - freq_below)) * (delta_phi_above - delta_phi_below))) % 360

            return delta_phi
        
        if ch == 1:
            return 0