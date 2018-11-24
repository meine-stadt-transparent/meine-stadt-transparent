import json


def get_importer(options):
    """
    We need this function because we (a) must not have a dependency on gi in the mainapp and (b) need to select
    over normal vs. Sternberg fixup.

    It query the system object to determine the vendor and the necessary workarounds.
    """

    from importer.oparl_resolve import OParlResolver

    resolver = OParlResolver(
        options["entrypoint"], options["cachefolder"], options["use_cache"]
    )

    system = json.loads(resolver.resolve(options["entrypoint"]).get_resolved_data())

    try:
        import gi

        gi.require_version("OParl", "0.4")
        from gi.repository import OParl
    except ImportError as e:
        if str(e) == "No module named 'gi'":
            raise ImportError(
                "You need to install liboparl for the importer. The readme contains the installation "
                "instructions"
            )
        else:
            raise e

    # This will likely need a more sophisticated logic in te future
    if system.get("contactName") == "STERNBERG Software GmbH & Co. KG":
        from importer.sternberg_import import SternbergImport as Importer
    else:
        from importer.oparl_import import OParlImport as Importer

    return Importer(options, resolver)
