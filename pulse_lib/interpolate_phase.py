import bisect

def interpolate_phase(freq, delta_phis):
    delta_phis = dict(sorted(delta_phis.items()))

    ind = bisect.bisect_left(list(delta_phis.keys()), freq)

    freq_above      = list(delta_phis.keys())[ind]
    delta_phi_above = delta_phis[list(delta_phis.keys())[ind]][0]
    freq_below      = list(delta_phis.keys())[ind-1]
    delta_phi_below = delta_phis[list(delta_phis.keys())[ind-1]][0]

    if abs(delta_phi_above - delta_phi_below) > 330:
        if delta_phi_above > delta_phi_below:
            delta_phi_below += 360
        elif delta_phi_above < delta_phi_below:
            delta_phi_above += 360

    delta_phi = (delta_phi_below + (((freq - freq_below) / (freq_above - freq_below)) * (delta_phi_above - delta_phi_below))) % 360

    return [delta_phi, 0]