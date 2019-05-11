# python-cmsis-svd-parser
Class for processing SVD documents and transforming those into a dictionary and 
back again! Supports 1.3 version of the CMSIS-SVD schema. Helps A LOT if you are 
trying to generate the header files for your MCU projects!

## What is returned
Dictionary returned after parsing is a nested one (obviously). Levels of 
hierarchy are as follows
* `device` - top of the dictionary
    * `cpu` - additional info about cpu employed in particular mcu
* `peripherals` - list of all peripherals
    * `interrups` - list of interrupts defined by the peripheral
* `clusters` | `registers` - peripheral may contain bare registers or clusters 
of registers. Clusters may be nested. Registers may not, obviously.
* `fields` - bit-fields of particular registers
* `enumerated_values` - name and list of enumerated values applicable for a 
given field
* `enumerated_value` - single enumerated value

## Usage
``` python
# import the xml parser
import xml.etree.ElementTree as ET
# import the svd reader/writer
from SVDWriter import SVDWriter
from SVDReader import SVDReader

# load the file using xml parser
root = ET.parse('example.svd').getroot()
# parse the device file
device = SVDReader.process(root)

#
# DO YOUR STUFF HERE
#

# process back to the xml tree
xml = SVDWriter.process(device, make_pretty=True)
# convert to string and save to file
open("test.svd", "wb").write(ET.tostring(xml))

```

## Example
Please see the Examples directory for a quick demonstration. Run the example by 
typing: `python ListPeriphRegs.py` or `python ReadWriteSVD.py` in the Examples 
directory

