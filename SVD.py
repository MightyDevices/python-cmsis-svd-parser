import xml.etree.ElementTree as ET
import re
import copy
import random
import string
from typing import List, Tuple


# class for parsing SVD files
class SVD:
    # levels of hierarchy in the system
    _hierarchy = ('device', 'peripherals',
                  'clusters', 'registers', 'fields',
                  'enumerated_values', 'enumerated_value')

    # do not derive these keys on these levels
    _derivation_exemptions = {
        'peripherals': ['interrupts']
    }

    # returns a list of next level hierarchy names that follow given node
    @staticmethod
    def _next_level_name(node: dict):
        return [h for h in SVD._hierarchy if h in node]

    # get to the next hierarchy level and return the list of tuples in format:
    # (level_name, level_collection). A list is returned because
    # registers/cluster can coexist on the same level (within peripherals or
    # nested clusters)
    @staticmethod
    def _next_level(node: dict):
        return [(h_name, node.get(h_name))
                for h_name in SVD._next_level_name(node)]

    # converts integer
    @staticmethod
    def _convert_integer(x: str):
        # try to perform the conversion
        try:
            value = int(x, 0)
        # oops!
        except ValueError:
            raise Exception("Unable to convert integer {x}")
        # report converted value
        return value

    # converts boolean value
    @staticmethod
    def _convert_boolean(x :str):
        # try to perform the conversion
        try:
            # word true provide
            if x.lower() == "true":
                value = True
            # word "false" provide
            elif x.lower() == "false":
                value = False
            # may be expressed as number
            else:
                value = bool(int(x, 0))
        # oops!
        except ValueError:
            raise Exception("Unable to convert integer {x}")
        # report converted value
        return value

    # converts string to non-negative integer
    @staticmethod
    def _convert_scaled_non_negative_integer(x: str):
        # try to convert
        try:
            # determine integer base yourself!
            value = int(x, 0)
            # these values shall not be negative
            if value < 0:
                raise ValueError
        # catch all
        except ValueError:
            raise Exception("Unable to convert scaledNonNegativeInteger {x}")
        # return the converted value
        return value

    # converts enumeratedValueDataType
    @staticmethod
    def _convert_enumerated_value_data_type(x: str):
        # allowable patterns
        patterns = [
            ("hex", "(0x|0X)[0-9a-fA-F]+"),
            ("dec", "[0-9]+"),
            ("bin", "(#|0b)[01xX]+")
        ]
        # allow plus sign
        regexp = "[+]?" + "|".join([f"(?P<{p[0]}>{p[1]})" for p in patterns])
        # try the conversion
        try:
            # try to match and con
            m = re.match(regexp, x).groupdict()
            # got hex value?
            if m.get('hex'):
                value = int(m.get('hex'), 16)
            # decimal number
            elif m.get('dec'):
                value = int(m.get('dec'), 10)
            # binary number with unused bits marked as '[xX]'
            else:
                # python can't handle '#' prefix
                python_bin = re.sub("#", "0b", m.get('bin'))
                # substitute unused bits for zeros
                value = int(re.sub("[xX]", "0", python_bin), 2)
        except Exception:
            raise Exception("Unable to convert enumeratedValueDataType {x}")
        # return the converted value
        return value

    # convert dim index type to an iterable that represents strings to be
    # substituted in the name placeholders
    @staticmethod
    def _convert_dim_index_type(x: str):
        # try to match against start-end syntax with numerals
        sen = re.match("(?P<start>[0-9]+|[A-Z]+)-(?P<end>[0-9]+|[A-Z]+)", x)
        # got a match?
        if sen:
            # starting and ending index
            start, end = int(sen.group('start')), int(sen.group('end'))
            # sanity check
            if start >= end:
                raise Exception(f"Invalid dim range, {x}")
            # produce a list of strings for substitution, this is inclusive
            # at the end
            return [str(n) for n in range(start, end + 1)]

        # try to match against start-end syntax with letters
        sel = re.match("(?P<start>[A-Z])-(?P<end>[A-Z])", x)
        # start-end letters syntax worked out!
        if sel:
            # starting and ending index
            start, end = ord(sen.group('start')), ord(sen.group('end'))
            # sanity check
            if start >= end:
                raise Exception(f"Invalid dim range, {x}")
            # produce a list of strings for substitution, this is inclusive
            # at the end
            return [chr(n) for n in range(start, end + 1)]

        # try to match against list syntax
        ls = re.match("([_0-9a-zA-Z]+)(?:,\s*([_0-9a-zA-Z]+))*", x)
        # list syntax worked out!
        if ls:
            return [ls.group(i) for i in range(1, len(ls.groups()))]

        # none of above worked out!
        raise Exception(f"Unable to convert dimIndexType {x}")

    # converter for identifiers compatible with ANSI C
    @staticmethod
    def _convert_identifier_type(x: str):
        # check name
        if not re.match("[_A-Za-z]+\w*", x):
            raise Exception(f"Unable to convert identifierType {x}")
        # return unchanged value
        return x

    # converter for 'dimable' name that follows ANSI C naming requirements
    @staticmethod
    def _covnert_dimable_identifier_type(x):
        # allowable variants
        variants = [
            "((%s)|(%s)[_A-Za-z]{1}\w*)",
            "([_A-Za-z]{1}\w*(\[%s\])?)",
            "([_A-Za-z]{1}[_A-Za-z0-9]*(%s)?[_A-Za-z0-9]*)"
        ]
        # match
        if not re.match("|".join(v for v in variants), x):
            raise Exception(f"Unable to convert dimableIdentifierType {x}")
        # return value
        return x

    # converter for bit range types
    @staticmethod
    def _convert_bit_range_type(x: str):
        # try to match
        m = re.match("\[((?:[0-6])?[0-9]):((?:[0-6])?[0-9])\]", x)
        if not m:
            raise Exception(f"Unable to convert bitRange {x}")
        # return the start-end tuple
        return int(m.group(1)), int(m.group(2))

    # converter cpu type
    @staticmethod
    def _convert_cpu_name_type(x: str):
        # allowed types
        types = [
            "CM0", "CM0PLUS", "CM0+", "CM1", "SC000", "CM23", "CM3",
            "CM33", "CM35P", "SC300", "CM4", "CM7", "ARMV8MML",
            "ARMV8MBL", "CA5", "CA7", "CA8", "CA9", "CA15", "CA17",
            "CA53", "CA57", "CA72", "other"
        ]
        # check if type belongs to set
        if not any(x in t for t in types):
            raise Exception(f"Invalid CPU type {x}")
        # report the type as string
        return x

    # converter for cpu revision
    @staticmethod
    def _convert_revision_type(x: str):
        # match against revision regexp
        if not re.match("r[0-9]*p[0-9]*", x):
            raise Exception(f"Invalid CPU revision {x}")
        # return as string
        return x

    # converter for endiannes
    @staticmethod
    def _convert_endian_type(x: str):
        # allowed types
        types = ["little", "big", "selectable", "other"]
        # check if type belongs to set
        if not any(x in t for t in types):
            raise Exception(f"Invalid CPU type {x}")
        # report the type as string
        return x

    # helper function to get value from xml tree. If the value is not present
    # then resort to default value. If convert is provided then use it to
    # convert the xml text (which is always a string, obviously) to whatever
    # you prefer
    @staticmethod
    def _get_val(node: ET.Element, name: str, default=None, convert=None,
                 required=True):
        # look for node
        rf = node.find(name)
        # no node
        if rf is None:
            # check when we expect the value to be present
            if required:
                raise Exception(f"Node {name} not present")
            # use the default value
            value = default
        # no text situation
        elif not rf.text:
            raise Exception(f"Node {name} does not contain any text")
        # node is valid
        else:
            # get rid of whitespaces
            text = re.sub("\s+", r" ", rf.text).rstrip()
            # cast if needed
            value = convert(text) if convert else text
        # return value
        return value

    # return a dictionary of values that are read from the node and are
    # convertedusing the conversion logic. convertsions is a list of tuples
    # in format: (dict_name, svd_name, required, default, converter)
    @staticmethod
    def _get_vals(node: ET.Element, conversions: list):
        # start with empty dictionary
        d = dict()
        # process all conversions
        for dict_name, svd_name, req, default, converter in conversions:
            d[dict_name] = SVD._get_val(node, svd_name, default, converter, req)
        # return entries that are not empty
        return {k: v for k, v in d.items() if v is not None}

    # generate random string that starts with '$' sign
    @staticmethod
    def _random_string(length=8):
        return "$" + ''.join(random.choices(string.hexdigits, k=length))

    # process cpu record
    @staticmethod
    def _process_cpu(node: ET.Element):
        # all the conversions
        conversions = [
            ('name', 'name', True, None, SVD._convert_cpu_name_type),
            ('revision', 'revision', True, None, SVD._convert_revision_type),
            ('endian', 'endian', True, None, SVD._convert_endian_type),
            ('mpu_present', 'mpuPresent', True, None, SVD._convert_boolean),
            ('fpu_present', 'fpuPresent', True, None, SVD._convert_boolean),
            ('nvic_priority_bits', 'nvicPrioBits', True, None,
             SVD._convert_integer),
            ('vendor_systick', 'vendorSystickConfig', True, None,
             SVD._convert_boolean),
        ]
        # return read values
        return SVD._get_vals(node, conversions)

    # process register property group
    @staticmethod
    def _process_register_properties_group(node: ET.Element):
        # all the conversions
        conversions = [
            ('size', 'size', False, None,
             SVD._convert_scaled_non_negative_integer),
            ('reset_value', 'resetValue', False, None,
             SVD._convert_scaled_non_negative_integer),
            ('reset_mask', 'resetMask', False, None,
             SVD._convert_scaled_non_negative_integer)
        ]
        # return read value
        return SVD._get_vals(node, conversions)

    # process dimensional element group
    @staticmethod
    def _process_dim_element_group(node: ET.Element):
        # all the conversions
        conversions = [
            ('dim', 'dim', False, None,
             SVD._convert_scaled_non_negative_integer),
            ('increment', 'dimIncrement', False, None,
             SVD._convert_scaled_non_negative_integer),
            ('index', 'dimIndex', False, None, SVD._convert_dim_index_type),
            ('name', 'dimName', False, None, SVD._convert_identifier_type)
        ]
        # return read value
        return SVD._get_vals(node, conversions)

    # process bit range
    @staticmethod
    def _process_bit_range(node: ET.Element):
        # all the conversions
        conversions = [
            ('offset', 'bitOffset', False, None,
             SVD._convert_scaled_non_negative_integer),
            ('width', 'bitWidth', False, None,
             SVD._convert_scaled_non_negative_integer),
            ('lsb', 'lsb', False, None,
             SVD._convert_scaled_non_negative_integer),
            ('msb', 'msb', False, None,
             SVD._convert_scaled_non_negative_integer),
            ('range', 'bitRange', False, None,
             SVD._convert_bit_range_type),
        ]
        # return read value
        return SVD._get_vals(node, conversions)

    # resolve processed bit-range to offset-width notation
    @staticmethod
    def _resolve_bit_range(bit_range: dict):
        # simplest case, offset and width already given
        if bit_range.get('offset') is not None:
            bit_offset = bit_range.get('offset')
            bit_width = bit_range.get('width', 1)
        # msb-lsb notation
        elif bit_range.get('lsb') is not None and bit_range.get('msb'):
            bit_offset = bit_range.get('lsb')
            bit_width = bit_range.get('msb') - bit_offset
        # range-notation
        elif bit_range.get('range') is not None:
            bit_offset, bit_width = bit_range.get('range')
        # unsupported case
        else:
            raise Exception("Unable to resolve bit range")
        # return processed information
        return bit_offset, bit_width

    # process address block
    @staticmethod
    def _process_address_block(node: ET.Element):
        # all the conversions
        conversions = [
            ('offset', 'offset', True, None,
             SVD._convert_scaled_non_negative_integer),
            ('size', 'size', True, None,
             SVD._convert_scaled_non_negative_integer),
            ('usage', 'usage', False, None, None),
        ]
        # return read value
        return SVD._get_vals(node, conversions)

    @staticmethod
    def _process_interrupt(node: ET.Element):
        # all the conversions
        conversions = [
            ('name', 'name', True, None, None),
            ('description', 'description', False, None, None),
            ('value', 'value', True, None, SVD._convert_integer),
        ]
        # do the conversions
        int_val = SVD._get_vals(node, conversions)
        # return read value
        return int_val.get('name'), int_val

    # process enumerated value
    @staticmethod
    def _process_enumerated_value(node: ET.Element):
        # all the conversions
        conversions = [
            ('name', 'name', False, None, None),
            ('header_name', 'headerEnumName', False, None,
             SVD._convert_identifier_type),
            ('value', 'value', False, None,
             SVD._convert_enumerated_value_data_type),
            ('is_default', 'isDefault', False, None,
             SVD._convert_boolean)
        ]
        # get basic information
        enum_val = SVD._get_vals(node, conversions)
        # these are always fully-defined
        enum_val['fully_defined'] = True
        # return name (which may be randomly generated if none is provided)
        # and read value
        return enum_val.get('name', SVD._random_string()), enum_val

    # process enumerated values
    @staticmethod
    def _process_enumerated_values(node: ET.Element):
        # all the conversions
        conversions = [
            ('name', 'name', False, None, None),
            ('header_name', 'headerEnumName', False, None,
             SVD._convert_identifier_type),
            ('description', 'description', False, None, None)
        ]
        # get basic information
        enums = SVD._get_vals(node, conversions)
        # derived field?
        if 'derivedFrom' in node.attrib:
            enums['derived_from'] = node.attrib['derivedFrom']
        # field is fully defined?
        else:
            enums['fully_defined'] = True
        # build up the field list
        enums['enumerated_value'] = dict()
        # process all values. we use 'iter' because enumeratedValue is
        # at the same level as 'node' itself
        for n in node.iter('enumeratedValue') or []:
            # process peripheral data
            ev_name, ev_data = SVD._process_enumerated_value(n)
            # store within the device
            enums['enumerated_value'][ev_name] = ev_data
        # return name (which may be randomly generated if none is provided)
        # and read value
        return enums.get('name', SVD._random_string()), enums

    # process fields that belong to registers
    @staticmethod
    def _process_field(node: ET.Element):
        # all the conversions
        conversions = [
            ('name', 'name', True, None, SVD._covnert_dimable_identifier_type),
            ('description', 'description', False, None, None)
        ]
        # get basic information
        field = SVD._get_vals(node, conversions)
        # registers property group may also be present
        field['reg_properties'] = SVD._process_register_properties_group(node)
        # dimensional element group might be present
        field['dim'] = SVD._process_dim_element_group(node)
        # resolve the notation to bit offset/bit_width
        field['bit_offset'], field['bit_width'] = \
            SVD._resolve_bit_range(SVD._process_bit_range(node))
        # derived field?
        if 'derivedFrom' in node.attrib:
            field['derived_from'] = node.attrib['derivedFrom']
        # field is fully defined?
        else:
            field['fully_defined'] = True
        # build up the field list
        field['enumerated_values'] = dict()
        # process all peripherals. we use 'iter' since these are on the same
        # level as the 'node'
        for n in node.iter('enumeratedValues') or []:
            # proces peripheral data
            evs_name, evs_data = SVD._process_enumerated_values(n)
            # store within the device
            field['enumerated_values'][evs_name] = evs_data
        # return read value
        return field.get('name'), field

    # process register information
    @staticmethod
    def _process_register(node: ET.Element):
        # all the conversions
        conversions = [
            ('name', 'name', True, None, SVD._covnert_dimable_identifier_type),
            ('description', 'description', False, None, None),
            ('offset', 'addressOffset', False, None,
             SVD._convert_scaled_non_negative_integer)
        ]
        # get basic information
        register = SVD._get_vals(node, conversions)
        # registers property group may also be present
        register['reg_properties'] = \
            SVD._process_register_properties_group(node)
        # dimensional element group might be present
        register['dim'] = SVD._process_dim_element_group(node)
        # derived register?
        if 'derivedFrom' in node.attrib:
            register['derived_from'] = node.attrib['derivedFrom']
        # register is fully defined?
        else:
            register['fully_defined'] = True
        # build up the field list
        register['fields'] = dict()
        # process all fields. we use 'find' to get to the children of the
        # 'fields' tag
        for n in node.find('fields') or []:
            # proces peripheral data
            f_name, f_data = SVD._process_field(n)
            # store within the device
            register['fields'][f_name] = f_data
        # return read value
        return register.get('name'), register

    # process cluster information. Note that clusters may be nested. Nested
    # clusters express hierarchical structures of registers (and make my life
    # miserable due to recursive programming which I hate).
    @staticmethod
    def _process_cluster(node: ET.Element):
        # all the conversions
        conversions = [
            ('name', 'name', True, None, SVD._covnert_dimable_identifier_type),
            ('description', 'description', False, None, None),
            ('offset', 'addressOffset', True, None,
             SVD._convert_scaled_non_negative_integer)
        ]
        # get basic information
        cluster = SVD._get_vals(node, conversions)
        # registers property group may also be present
        cluster['reg_properties'] = SVD._process_register_properties_group(node)
        # dimensional element group might be present
        cluster['dim'] = SVD._process_dim_element_group(node)
        # derived register?
        if 'derivedFrom' in node.attrib:
            cluster['derived_from'] = node.attrib['derivedFrom']
        # register is fully defined?
        else:
            cluster['fully_defined'] = True

        # start with an empty dictionary
        cluster['clusters'] = dict()
        # clusters may contain nested clusters. how neat.
        for n in node.findall('cluster') or []:
            # go down the cluster tree
            c_name, c_data = SVD._process_cluster(n)
            # store information
            cluster['clusters'][c_name] = c_data

        # cluster may also contain registers
        cluster['registers'] = dict()
        # process registers
        for n in node.findall('register') or []:
            # process peripheral data
            r_name, r_data = SVD._process_register(n)
            # store within the device
            cluster['registers'][r_name] = r_data

        # return data
        return cluster.get('name'), cluster

    # process single peripheral, return derivation path as well
    @staticmethod
    def _process_peripheral(node: ET.Element):
        # all the conversions
        conversions = [
            ('name', 'name', True, None, SVD._covnert_dimable_identifier_type),
            ('group_name', 'groupName', False, None, None),
            ('description', 'description', False, None, None),
            ('base_address', 'baseAddress', True, None,
             SVD._convert_scaled_non_negative_integer)
        ]
        # get basic information
        peripheral = SVD._get_vals(node, conversions)
        # registers property group may also be present
        peripheral['reg_properties'] = \
            SVD._process_register_properties_group(node)
        # dimensional element group might be present
        peripheral['dim'] = SVD._process_dim_element_group(node)
        # derived peripheral?
        if 'derivedFrom' in node.attrib:
            peripheral['derived_from'] = node.attrib['derivedFrom']
        # peripheral is fully defined?
        else:
            peripheral['fully_defined'] = True

        # process address block (it might be not present)
        if node.find('addressBlock'):
            peripheral['address_block'] = \
                SVD._process_address_block(node.find('addressBlock'))

        # initialize with empty dictionary
        peripheral['interrupts'] = dict()
        # a peripheral may have multiple interrupts
        for n in node.findall('interrupt'):
            # parse interrupt record
            i_name, i_data = SVD._process_interrupt(n)
            # store
            peripheral['interrupts'][i_name] = i_data

        # registers stag encapsulates the clusters and register definitions
        node_registers = node.find('registers')
        # node registers
        if node_registers:
            # prepare placeholders for both: registers and clusters
            peripheral['registers'], peripheral['clusters'] = dict(), dict()
            # process clusters
            for n in node_registers.findall('cluster'):
                # go down the cluster tree
                c_name, c_data = SVD._process_cluster(n)
                # store information
                peripheral['clusters'][c_name] = c_data

            # process clusters
            for n in node_registers.findall('register'):
                # go down the cluster tree
                c_name, c_data = SVD._process_register(n)
                # store information
                peripheral['registers'][c_name] = c_data

        # return read value
        return peripheral.get('name'), peripheral

    # process the device entry
    @staticmethod
    def _process_device(node: ET.Element):
        # all the conversions
        conversions = [
            ('name', 'name', True, None, None),
            ('description', 'description', True, None, None),
            ('version', 'version', True, None, None)
        ]
        # convert all the device fields
        device = SVD._get_vals(node, conversions)
        # store the information about the cpu
        device['cpu'] = SVD._process_cpu(node.find('cpu'))
        # registers property group may also be present
        device['reg_properties'] = SVD._process_register_properties_group(node)
        # build up the peripheral list
        device['peripherals'] = dict()
        # devices are always fully defined
        device['fully_defined'] = True
        # process all peripherals
        for n in node.find('peripherals') or []:
            # process peripheral data
            p_name, p_data = SVD._process_peripheral(n)
            # store within the device
            device['peripherals'][p_name] = p_data
        # return read value
        return device

    # update all the fields of 'update_to' with fields from 'update_from'.
    # 'update_to' is our working dictionary.
    @staticmethod
    def _update_elements(update_to: dict, update_from: dict, overwrite=True,
                         exemptions=None):
        # process key-value pairs from the source ('from') dictionary
        for k in update_from:
            # skip all the entries that we do not want to propagate
            if exemptions and k in exemptions:
                continue
            # if entry exists in 'from' but not in 'to' then it is copied
            # using deepcopy as it may contain nested dictionaries
            if k not in update_to:
                update_to[k] = copy.deepcopy(update_from[k])
            # both entries exist and both are dictionaries, need to go deeper
            elif isinstance(update_to[k], dict) and \
                    isinstance(update_from[k], dict):
                SVD._update_elements(update_to[k], update_from[k], overwrite)
            # 'other types
            elif overwrite:
                update_to[k] = copy.deepcopy(update_from[k])

    # function walks the derivation path and returns the matching entry
    @staticmethod
    def _follow_derivation_path(path: str, level_collections: list):
        # split path using periods
        path_elems = path.split(".")
        # if path is more parts that we have level collections then there is
        # something fishy about it!
        if len(level_collections) < len(path_elems):
            raise Exception("path {path} levels exceed the number of hierarchy "
                            "'levels' provided")
        # both: absolute and relative cases are handled here
        else:
            # when looking into absolute path start from the very beginning of
            # the levels provided. For relative paths (path_elems is shorter
            # than level_collections)
            lc = level_collections[-len(path_elems)]
            # this will hold the collection that matches path element on the
            # level that we are currently processing
            found_col = None
            # process every part in path
            for p in path_elems:
                # reset
                found_col = None
                # do we have the name present among the list
                for level_name, level_collection in lc:
                    found_col = found_col or level_collection.get(p)
                # nothing was found?
                if found_col is None:
                    break
                # got a match! go to next level
                else:
                    lc = SVD._next_level(found_col)
            # store result
            result = found_col
        # oops! nothing was found!
        if result is None:
            raise Exception(f"Path {path} is unreachable within provided level "
                            f"collection")
        # return the result
        return result

    # function used to construct the derivation list for nested derivations,
    # list contains all elements that we derive from until a non-derived element
    # is found (which is the last element on the list). For example if current
    # element A derives from B which derives from C then the list will be as
    # follows: [B, C]
    @staticmethod
    def _build_derivation_list(elem: dict, level_collections: list):
        # the infamous derivation list
        derivation_list = [elem]
        # go in depth
        while elem.get('derived_from') and not elem.get('fully_defined'):
            # get the derived element
            derived_from = SVD._follow_derivation_path(elem['derived_from'],
                                                       level_collections)
            # add to list
            derivation_list += [derived_from]
            # update the element
            elem = derived_from
        # return the gathered information
        return derivation_list

    # function used to merge all the elements from the derivation list
    @staticmethod
    def _apply_derivation_list(derivation_list: list, level_name: str):
        # start with the empty dictionary. we also return all the element that
        # had their derivations resolved along the way
        output, output_list = dict(), []
        # do we have any exemptions for this level
        level_exemptions = SVD._derivation_exemptions.get(level_name)
        # process derivation list
        for level_collection in reversed(derivation_list):
            # udpate the current output with data from 'd'
            SVD._update_elements(output, level_collection,
                                 exemptions=level_exemptions)
            # store the state on the list
            output_list.append(copy.deepcopy(output))
        # return a list that represents all the steps of the derivation
        return reversed(output_list)

    # generate element instances based on the 'derivedFrom' property
    @staticmethod
    def _resolve_derivations(node: dict, name=None, level_name='device',
                             levels_collections=None):
        # initialize list that represent the levels that we reach as we go
        # down the hierarchy
        if levels_collections is None:
            levels_collections = []

        # obtain a list of collections for the next level in hierarchy
        next_level_collections = SVD._next_level(node)
        # element derives from something?
        if not node.get('fully_defined'):
            # build the list of all things that we derive from
            dl = SVD._build_derivation_list(node, levels_collections)
            # produce merged outputs on all levels of derivation, zip these with
            # current values of elements  that were used for the whole
            # derivation process and finally update them with derived data.
            # 'update()' is safe here since '_apply_derivation_list()' produces
            # deep-copies of the data provided
            for dst, src in zip(dl, SVD._apply_derivation_list(dl, level_name)):
                dst.update(src)

            # enumerated value[s] do not need to have their name specified and
            # so it might be a subject of change. If enumerated value 'name'
            # field differs than the key-name that is is availabe under in the
            # collection then we shall use the derived name
            new_name = node.get('name')
            # those two differ?
            if name != new_name:
                # get the collections for current level
                level_collections = levels_collections[-1]
                # look for one with the matching name
                for col_name, col in level_collections:
                    # if found then change the key
                    if name in col:
                        col[new_name] = col.pop(name)
                        break

        # this process goes as far as registers go
        for next_level_name, next_level_collection in next_level_collections:
            # go in depth
            for name, elem in next_level_collection.items():
                # we update level collections here so that a new list is created
                # and we don't mess up the lists from  previous calls of this
                # recursive function
                SVD._resolve_derivations(elem, name, next_level_name,
                                         levels_collections +
                                         [next_level_collections])

    # process all the fields that have the following property: elements of lower
    # level group overwrite the elements from more general level. Currently this
    # deals with 'registerPropertiesGroup' but you can add more in the
    # 'initial conditions'
    @staticmethod
    def _resolve_implicit_inheritance(node: dict, inheritance=None):
        # initial conditions
        if inheritance is None:
            inheritance = {k: dict() for k in ['reg_properties']}

        # dive into the hierarchy levels
        next_level_collections = SVD._next_level(node)
        # process every entry within the inheritance
        for k in inheritance:
            # update with what was inherited
            SVD._update_elements(node[k], inheritance[k], overwrite=False)
            # this is now our new inheritance
            inheritance[k] = node.get(k)

        # process all collections
        for next_level_name, next_level_collection in next_level_collections:
            # this process goes as far as registers go
            if next_level_name != 'fields':
                # go in depth
                for name, elem in next_level_collection.items():
                    SVD._resolve_implicit_inheritance(elem, inheritance)

    # create an iterable that represents all strings that shall be generated
    # based on provided 'dimElementGroup' data
    @staticmethod
    def _create_arrays_lists_namespace(node: dict):
        # extract information
        name, dim = node.get('name'), node.get('dim')
        # two modes of operation
        is_array = "[%s]" in name
        is_list = not is_array and "%s" in name
        # array generates a single entry in form name[length] and with offset 0
        if is_array:
            # this is the trick to serving an array
            namespace = [(re.sub("%s", f"{dim.get('dim')}", name), 0)]
        # list situation
        elif is_list:
            # construct a range using provided list of indices or range
            # determined by dim
            rng = dim.get('index', [str(i) for i in range(dim.get('dim', 0))])
            inc = dim.get('increment')
            # invalid parameteres?
            if not rng or not inc:
                raise Exception(f"List requires either dim or dim_index")
            # build up the list
            namespace = [(re.sub("%s", rng[i], name), inc * i)
                         for i in range(len(rng))]
        # sanity check
        else:
            raise Exception("No placeholder '%s' within name string")
        # return the resulting namespace
        return namespace

    # create instances based on the dim information provided
    @staticmethod
    def _create_arrays_lists(node: dict, level: str):
        # nothing to work on
        if "%s" not in node.get('name'):
            return None
        # level-offset field name lookup table
        lut = {
            'peripherals': 'base_address',
            'registers': 'offset',
            'clusters': 'offset',
            'fields': 'bit_offset'
        }
        # list of produced nodes
        nodes = []
        # process every name
        for name, offset in SVD._create_arrays_lists_namespace(node):
            # create new dictionary
            new_node = dict(node)
            # set name
            new_node['name'] = name
            # reset dim structure as we are done with dimming
            new_node['dim'] = dict()
            # use the dim increment generated offset to update node offset
            new_node[lut[level]] = new_node.get(lut[level], 0) + offset
            # return generator
            nodes += [new_node]
        # return all the nodes that were created
        return nodes

    # resolve dimensional information to produce arrays and lists
    @staticmethod
    def _resolve_arrays_lists(node: dict, level_name='device', parent=None):
        # next hierarchy level name
        next_level_collections = SVD._next_level(node)
        # create nodes based on array/list generation
        new_nodes = SVD._create_arrays_lists(node, level_name)
        # got the substitution list?
        if new_nodes:
            # pop the old one
            parent.pop(node['name'])
            # append the new ones
            for nn in new_nodes:
                parent[nn['name']] = nn

        # process all collections
        for next_level_name, next_level_collection in next_level_collections:
            # this process goes as far as fields
            if next_level_name != 'enumerated_values':
                # go in depth
                for name, elem in next_level_collection.items():
                    SVD._resolve_arrays_lists(elem, next_level_name,
                                              next_level_collection)

    # process the device from the root of the svd document.If the processing
    # succeeds then a dictionary will be returned in which the structure of the
    # device will be contained. All the derivations and inheritances are getting
    # taken care of so the dictionary will be a top-down tree (without any
    # cycles or other funny-business). That, my dear friend should help you in
    # cases such as generating your own *.h files for MCU projects.
    @staticmethod
    def process(root: ET.Element):
        # build up the device dictionary as defined in the svd file
        device = SVD._process_device(root)

        # resolve all derivations so that we end up with fully expanded
        # list of peripherals/registers/etc...
        SVD._resolve_derivations(device)
        # resolve the inheritance within the device tree according
        # to svd rules
        SVD._resolve_implicit_inheritance(device)
        # # create lists and arrays!
        SVD._resolve_arrays_lists(device)

        # return the processed device
        return device
