from qick import *
import numpy as np

class CalibratePhase(AveragerProgram):
    def __init__(self,soccfg, cfg):
        super().__init__(soccfg, cfg)

    def initialize(self):
        cfg = self.cfg
        soccfg = self.soccfg

        # configure the readout lengths and downconversion frequencies
        for ch in [0,1]:
            self.declare_readout(ch=ch, length=1000, # [Clock cycles]
                                 freq=self.cfg["pulse_freq"])
            self.declare_gen(ch=ch, nqz=1)
        
        freq = soccfg.freq2reg(cfg['pulse_freq'])  # convert frequency to dac frequency
        phases = [0,0]
        gains = [20000,20000]

        self.trigger(pins=[0], t=0) # send a pulse on pmod0_0, for scope trigger
        for ch in [0,1]:
            self.set_pulse_registers(ch=ch, style="const", freq=freq, phase=self.deg2reg(phases[ch]), gain=gains[ch], mode="periodic", length=self.us2cycles(10, gen_ch=ch))

        self.synci(200)  # give processor some time to configure pulses
    
    def body(self):
        self.trigger(adcs=[0,1],adc_trig_offset=1000) # [Clock cycles]
        for ch in [0,1]:
            self.pulse(ch=ch, t=0)

        self.wait_all()
        self.sync_all(200)
    
    def calculate_phase(self, d):
        [xi,xq] = d
        x = xi +1j*xq

        # Average to improve calibration.
        xavg = np.mean(x)

        # print(x)
        # print(xavg)

        # Calculate calibration phase.
        fi = np.remainder(np.angle(xavg,deg=True)+360,360)
        # return [fi, np.abs(xavg), np.std(x)]
        return fi