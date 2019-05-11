import xml.etree.ElementTree as ET


# class for writing the svd files from dictionary produced by the svd
# parser
class SVDWriter:
    # converter for boolean values (we use integer strings so that the schema
    # does not yell at us for using 'True' and 'False'
    @staticmethod
    def _convert_bool(x):
        return '1' if x else '0'

    # converter for string values
    @staticmethod
    def _convert_str(x):
        return str(x)

    # convert to hex number
    @staticmethod
    def _convert_hex(x):
        return f"{x:#010x}"

    # convert dim index list
    @staticmethod
    def _convert_dim_index_type(x):
        return ",".join(x)

    # make the xml look pretty using the tail attribute which is a string
    # appended after the tag is closed
    @staticmethod
    def _make_pretty(elem: ET.Element, indentation="\t", level=0):
        # spacer logic
        i = "\n" + level * indentation
        # elements
        if len(elem):
            # element with no text - put a newline and indentation
            if not elem.text or not elem.text.strip():
                elem.text = i + "\t"
            # closing sequence for the current element
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            # go down recursively
            for elem in elem:
                SVDWriter._make_pretty(elem, indentation, level + 1)
            # recursive function did not produce tail
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        # elements without sub-elements go here
        else:
            # end with newline and indentation
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    # populates an xml tree with elements with data from dictionary after
    # mapping and conversion. conversion is a dict keyed by the field names
    # from the data dictionary and contains tuples as values in form:
    # (xml_node_name, conversion function (None for str(x) conversion)).
    # If a key does not exist in 'conversions' then the value is rewritten to
    # xml one-to-one basis
    @staticmethod
    def _build_tree(tree: ET.Element, data: dict, conversions: dict):
        # do the conversion
        for name, v in conversions.items():
            # no data
            if name not in data:
                continue
            # none given
            if v is None:
                value = None, None
            # string was given
            elif isinstance(v, str):
                value = v, None
            # is callable?
            elif callable(v):
                value = None, v
            # full tuple given
            else:
                value = v
            # get converter for currently processed data element
            xml_name, xml_conv = value
            # defaults
            xml_name = xml_name or name
            xml_conv = xml_conv or SVDWriter._convert_str
            # build up the sub-element
            se = ET.SubElement(tree, xml_name)
            # set text value
            se.text = xml_conv(data[name])
        # return the tree
        return tree

    # fill the information regarding the registerPropertiesGroup type
    @staticmethod
    def _append_register_properties_group(xml: ET.Element,
                                          reg_properties: dict):
        # build tree
        SVDWriter._build_tree(xml, reg_properties, {
            'size': None,
            'reset_value': ('resetValue', SVDWriter._convert_hex),
            'reset_mask': ('resetMask', SVDWriter._convert_hex)
        })

    # fill the dimensional information
    @staticmethod
    def _append_dim_element_group(xml: ET.Element, dim: dict):
        # prepare basic information
        SVDWriter._build_tree(xml, dim, {
            'dim': None,
            'increment': 'dimIncrement',
            'index': ('dimIndex', SVDWriter._convert_dim_index_type)
        })

    # prepare information about a single enumerated value
    @staticmethod
    def _populate_enumerated_value(enumerated_value: dict):
        # return the enumerated value sub-tree
        return SVDWriter._build_tree(ET.Element('enumeratedValue'),
                                     enumerated_value, {
            'name': None,
            'description': None,
            'value': None,
            'is_default': ('isDefault', SVDWriter._convert_bool)
        })

    # prepare information about a group of enumerated values
    @staticmethod
    def _populate_enumerated_values(enumerated_values: dict):
        # create a root
        xml_enumerated_values = ET.Element('enumeratedValues')
        # got the derivation set-up?
        if not enumerated_values.get('fully_defined'):
            xml_enumerated_values.set('derivedFrom',
                                      enumerated_values['derived_from'])
        # build up the basic information
        SVDWriter._build_tree(xml_enumerated_values,
                              enumerated_values, {'name': None})
        # process all fields within register
        if enumerated_values.get('enumerated_value'):
            for _, ev in enumerated_values['enumerated_value'].items():
                xml_enumerated_values.append(
                    SVDWriter._populate_enumerated_value(ev))
        # return the generated tree
        return xml_enumerated_values

    # prepare a sub-tree containing information about a single field
    @staticmethod
    def _populate_field(field: dict):
        # root element for the register
        xml_field = ET.Element('field')
        # got the derivation set-up?
        if not field.get('fully_defined'):
            xml_field.set('derivedFrom', field['derived_from'])
        # prepare basic information
        SVDWriter._build_tree(xml_field, field, {
            'name': None,
            'description': None,
            'bit_offset': 'bitOffset',
            'bit_width': 'bitWidth',
        })
        # multiple enumerated values are supported
        if field.get('enumerated_values'):
            for _, evs in field['enumerated_values'].items():
                xml_field.append(SVDWriter._populate_enumerated_values(evs))
        # return the tree
        return xml_field

    # prepare tree of fields
    @staticmethod
    def _populate_fields(register: dict):
        # create a root
        xml_fields = ET.Element('fields')
        # process all fields within register
        for _, f in register['fields'].items():
            xml_fields.append(SVDWriter._populate_field(f))
        # return the generated tree
        return xml_fields

    # write a single register information
    @staticmethod
    def _populate_register(register: dict):
        # root element for the register
        xml_register = ET.Element('register')
        # got the derivation set-up?
        if not register.get('fully_defined'):
            xml_register.set('derivedFrom', register['derived_from'])
        # populate dim information
        if register.get('dim'):
            SVDWriter._append_dim_element_group(xml_register, register['dim'])
        # prepare basic information
        SVDWriter._build_tree(xml_register, register, {
            'name': None,
            'description': None,
            'offset': ('addressOffset', SVDWriter._convert_hex)
        })
        # populate registers properties information
        if register.get('reg_properties'):
            SVDWriter._append_register_properties_group(
                xml_register, register['reg_properties'])
        # store register fields
        if register.get('fields'):
            xml_register.append(SVDWriter._populate_fields(register))
        # return the xml representing the register
        return xml_register

    # write cluster information (may be recursive)
    @staticmethod
    def _populate_cluster(cluster: dict):
        # prepare root for the cluster
        xml_cluster = ET.Element('cluster')
        # got the derivation set-up?
        if not cluster.get('fully_defined'):
            xml_cluster.set('derivedFrom', cluster['derived_from'])
        # populate dim information
        if cluster.get('dim'):
            SVDWriter._append_dim_element_group(xml_cluster, cluster['dim'])
        # prepare basic information
        SVDWriter._build_tree(xml_cluster, cluster, {
            'name': None,
            'description': None,
            'offset': ('addressOffset', SVDWriter._convert_hex),
        })
        # populate registers properties information
        if cluster['reg_properties']:
            SVDWriter._append_register_properties_group(
                xml_cluster, cluster['reg_properties'])
        # support for nested clusters
        if cluster.get('clusters'):
            for _, c in cluster['clusters'].items():
                xml_cluster.append(SVDWriter._populate_cluster(c))
        # prepare register information
        if cluster.get('registers'):
            for _, r in cluster['registers'].items():
                xml_cluster.append(SVDWriter._populate_register(r))
        # return gathered information
        return xml_cluster

    # write registers information
    @staticmethod
    def _populate_registers(peripheral: dict):
        # registers root element
        xml_registers = ET.Element('registers')
        # process every cluster
        if peripheral.get('clusters'):
            for _, c in peripheral['clusters'].items():
                xml_registers.append(SVDWriter._populate_cluster(c))
        # process every peripheral
        if peripheral.get('registers'):
            for _, r in peripheral['registers'].items():
                xml_registers.append(SVDWriter._populate_register(r))
        # return peripherals
        return xml_registers

    # prepare subtree containing information about a single interrupt
    @staticmethod
    def _populate_interrupt(interrupt: dict):
        # build a single interrupt sub-node
        return SVDWriter._build_tree(ET.Element('interrupt'), interrupt, {
            'name': None,
            'value': None
        })

    # populate single peripheral information
    @staticmethod
    def _populate_peripheral(peripheral: dict):
        # root peripheral element
        xml_peripheral = ET.Element('peripheral')
        # got the derivation set-up?
        if not peripheral.get('fully_defined'):
            xml_peripheral.set('derivedFrom', peripheral['derived_from'])
        # populate dim information
        if peripheral.get('dim'):
            SVDWriter._append_dim_element_group(xml_peripheral,
                                                peripheral['dim'])
        # populate basic information
        SVDWriter._build_tree(xml_peripheral, peripheral, {
            'name': None,
            'description': None,
            'group_name': 'groupName',
            'base_address': ('baseAddress', SVDWriter._convert_hex)
        })
        # populate registers properties information
        if peripheral.get('reg_properties'):
            SVDWriter._append_register_properties_group(
                xml_peripheral, peripheral['reg_properties'])
        # store interrupt information
        if peripheral.get('interrupts'):
            for _, i in peripheral['interrupts'].items():
                xml_peripheral.append(SVDWriter._populate_interrupt(i))
        # populate registers information
        if peripheral.get('registers'):
            xml_peripheral.append(SVDWriter._populate_registers(peripheral))
        # return the populated peripheral
        return xml_peripheral

    # write peripherals
    @staticmethod
    def _populate_peripherals(device: dict):
        # peripherals root element
        xml_peripherals = ET.Element('peripherals')
        # process every peripheral
        for k, v in device['peripherals'].items():
            xml_peripherals.append(SVDWriter._populate_peripheral(v))
        # return peripherals
        return xml_peripherals

    # write device cpu information
    @staticmethod
    def _populate_cpu(device: dict):
        # populate the entries
        return SVDWriter._build_tree(ET.Element('cpu'), device['cpu'], {
            'name': None,
            'revision': None,
            'endian': None,
            'mpu_present': ('mpuPresent', SVDWriter._convert_bool),
            'fpu_present': ('fpuPresent', SVDWriter._convert_bool),
            'nvic_priority_bits': 'nvicPrioBits',
            'vendor_systick': ('vendorSystickConfig', SVDWriter._convert_bool),
        })

    # write device description
    @staticmethod
    def _populate_device(device: dict):
        # list of all root node attributes
        attributes = {
            'schemaVersion': "1.3",
            'xmlns:xs': "http://www.w3.org/2001/XMLSchema-instance",
            'xs:noNamespaceSchemaLocation': "CMSIS-SVD.xsd",
        }
        # build the root entry
        root = ET.Element('device', attrib=attributes)
        # append basic information
        SVDWriter._build_tree(root, device, {
            'name': None,
            'version': None,
            'description': None,

        })
        # append the cpu information
        root.append(SVDWriter._populate_cpu(device))
        # append basic information
        SVDWriter._build_tree(root, device, {
            'address_unit_bits': 'addressUnitBits',
            'width': None,
        })

        # append peripheral information
        root.append(SVDWriter._populate_peripherals(device))
        # return the xml root node element
        return root

    # process the device describing dictionary as produced by the svd parser
    @staticmethod
    def process(device: dict, make_pretty=True, **kwargs):
        # process device
        xml_device = SVDWriter._populate_device(device)
        # add whitespaces, newlines tabs, etc.. to make the xml more readable
        # when converted to string
        if make_pretty:
            SVDWriter._make_pretty(xml_device, **kwargs)
        # return gathered data
        return xml_device
