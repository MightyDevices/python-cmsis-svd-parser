import copy
import re

# utility class
class SVDUtils:
    # filter dict entries using regexp matching key name
    @staticmethod
    def filter(data: dict, regexp: str) -> dict:
        return {k: data[k] for k in data if re.match(regexp, k, re.IGNORECASE)}

    # return the sorted version (list of tuples) of the dictionary
    @staticmethod
    def sort(d: dict, key: str) -> list:
        return sorted(d.items(), key=lambda kv: kv[1][key])

    # merge two dictionaries
    @staticmethod
    def merge_dicts(merge_to: dict, merge_from: dict, overwrite=True,
                    exempltions=None):
        # start with an dictionary that is a deep copy of the merge_to
        output = copy.deepcopy(merge_to)
        # merge all entries from 'from'
        for k in merge_from:
            # skip
            if exempltions and k in exempltions:
                continue
            # key not present - copy it
            if k not in output:
                output[k] = copy.deepcopy(merge_from[k])
            # both entries are dicts
            elif isinstance(output[k], dict) and \
                    isinstance(merge_from[k], dict):
                # go in-depth
                output[k] = SVDUtils.merge_dicts(output[k], merge_from[k],
                                                 overwrite)
            # other types simply overwrite
            elif overwrite:
                output[k] = copy.deepcopy(merge_from[k])
        # return merged data
        return output

    # build a default peripheral that can be incorporated into the svd file
    @staticmethod
    def build_peripheral(name, base_address, **kwargs):
        # optional fields
        field_names = ['group_name', 'description', 'alternate_to',
                       'header_struct_name', 'registers', 'clusters']
        # shove in the mandatory fields
        peripheral = {
            'name': name,
            'base_address': base_address,
        }
        # apply optional fields
        peripheral.update({k: v for k, v in kwargs.items() if k in field_names})
        # return the constructed peripheral
        return peripheral

    # construct a dimensional information group
    @staticmethod
    def build_dim(dimension, increment, **kwargs):
        # optional fields
        field_names = ['name', 'index']
        # shove in the mandatory fields
        dim = {
            'dim': dimension,
            'increment': increment
        }
        # apply optional fields
        dim.update({k: v for k, v in kwargs.items() if k in field_names})
        # return the constructed block
        return dim


