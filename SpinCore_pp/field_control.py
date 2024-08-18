from Instruments.XEPR_eth import xepr
import pyspecdata as psd
import logging


def set_field(config_dict):
    """Sets the field based on the carrier frequency and effective gamma
    inside the configuration file where the effective gamma is the ratio
    between the NMR frequency (in MHz) and the field (in G)"""
    Field_G = config_dict["carrierFreq_MHz"] / config_dict["gamma_eff_MHz_G"]
    with xepr() as x:
        assert Field_G < 3700, (
            "Are you mad?? The field you want, %g, is too high!" % Field_G
        )
        assert Field_G > 3300, (
            "Are you mad?? The field you want, %g, is too low!" % Field_G
        )
        Field_G = x.set_field(Field_G)
        logging.info(psd.strm("Field set to ", Field_G))
    return
