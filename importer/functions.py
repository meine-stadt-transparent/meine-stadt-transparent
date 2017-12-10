def get_importer(options=None):
    """
    We need this function because we (a) must not have a dependency on gi in the mainapp and (b) need to select
    over normal vs. Sternberg fixup.
    """
    try:
        if options and options["use_sternberg"]:
            from importer.sternberg_import import SternbergImport as Importer
        else:
            from importer.oparl_import import OParlImport as Importer
    except ImportError as e:
        if str(e) == "No module named 'gi'":
            raise ImportError("You need to install liboparl for the importer. The readme contains the installation "
                              "instructions")
        else:
            raise e

    return Importer
