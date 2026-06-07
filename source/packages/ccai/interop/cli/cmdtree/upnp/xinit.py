
import click


from ccai.interop.cli.cmdtree.upnp.generate import command_am_interop_upnp_generate
from ccai.interop.cli.cmdtree.upnp.scan import command_am_interop_upnp_scan

@click.group("upnp", help="Contains commands for working with the UPnP protocol.")
def group_am_interop_upnp():
    return

group_am_interop_upnp.add_command(command_am_interop_upnp_generate)
group_am_interop_upnp.add_command(command_am_interop_upnp_scan)

def register_groups(parent: click.Group):
    parent.add_command(group_am_interop_upnp)
    return