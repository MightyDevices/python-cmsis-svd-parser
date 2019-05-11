# This example reads the input file, converts to dictionary and then writes back
# to output svd file
# add the top directory where the module itself sits
import site
site.addsitedir("..")


# import the xml parser
import xml.etree.ElementTree as ET
# import the svd reader/writer
from SVDWriter import SVDWriter
from SVDReader import SVDReader

# load the file using xml parser
root = ET.parse('example.svd').getroot()
# parse the device file
device = SVDReader.process(root)
# process back to the xml tree
xml = SVDWriter.process(device, make_pretty=True)

# convert to string and save to file
open("test.svd", "wb").write(ET.tostring(xml))

