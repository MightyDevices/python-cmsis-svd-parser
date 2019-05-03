# In this example we are about to list all registers of all peripherals after
# being processed by the main hero of this story

import xml.etree.ElementTree as ET

# import the svd parser itself
from SVD.SVD import SVD


# display information about the registers fields and whatnot
def display_fields(register: dict, level=0):
    # parse all fields
    for field in register['fields']:
        # show field name
        print("\t" * level + f"Field Name: {field}")


# do a recursive browsing of the cluster/register tree
def display_registers(collection: dict, level=0):
    # got a cluster situation?
    if 'clusters' in collection:
        # clusters may come in multiples
        for cluster in collection['clusters']:
            # show it's name
            print("\t" * level + f"Cluster Name: {cluster}")
            # go down recursively since clusters may be nested!
            display_registers(collection['clusters'][cluster], level + 1)
    # got a register situation?
    if 'registers' in collection:
        # registers may come in multiples
        for register in collection['registers']:
            # show it's name
            print("\t" * level + f"Register Name: {register}")
            # go down!
            display_fields(collection['registers'][register], level + 1)


# load the file using xml parser
root = ET.parse('example.svd').getroot()
# parse the device file
device = SVD.process(root)

# show the device name
print(f"Device name: {device['name']}")
# for every peripheral
for p in device['peripherals']:
    # .. show it's name
    print(f"Peripheral name: {p}")
    # and browse it's registers (either free-running or grouped in clusters)
    display_registers(device['peripherals'][p], level=1)
