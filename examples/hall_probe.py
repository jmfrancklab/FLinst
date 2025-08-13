from Instruments import LakeShore475, prologix_connection


with prologix_connection() as p:
    with LakeShore475(p) as g:
        # print(g.identify())
        print(g.read_field())

        """
        gauss.set_field_units(1) #Sets units to G. Use 2 to set units in T.
        if not gauss.is_auto(): #Makes sure that the auto range is enabled
            gauss.enable_auto_range(1)
        time.sleep(1)
        field = gauss.read_field()  #Reading the field
        print(f"Magnetic field: {field:.3f} G")
        """
