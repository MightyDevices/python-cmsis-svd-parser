import copy


# utility class
class SVDUtils:
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
