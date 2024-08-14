from Instruments.XEPR_eth import xepr
import pyspecdata as psd

def set_field(config_dict):
    """Ensures the field is appropriate before setting the desired field."""
    Field_G = config_dict["carrierFreq_MHz"] / config_dict["gamma_eff_MHz_G"]
    with xepr() as x:
        assert Field_G < 3700, (
            "Are you mad?? The field you want, %g, is too high!" % Field_G
        )
        assert Field_G > 3300, (
            "Are you mad?? The field you want, %g, is too low!" % Field_G
        )
        Field_G = x.set_field(Field_G)
        psd.logger.info(psd.strm("Field set to ", Field_G))
    return
