def merge_dicts(d1, d2):
    """
    Updates d1 from d2 by replacing each (k, v1) pair in d1 with the
    corresponding (k, v2) pair in d2.

    If the value of each pair is itself a dict, then the value is updated
    recursively.
    """

    new_dict = d1.copy()

    for k, v in d2.items():
        if isinstance(new_dict.get(k), dict) and isinstance(v, dict):
            new_dict[k] = merge_dicts(new_dict[k], d2[k])
        else:
            new_dict[k] = d2[k]
    return new_dict


class DotDict(dict):
    """
    A dict that also supports attribute ("dot") access
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def __repr__(self):
        return 'DotDict({})'.format(super().__repr__())


def dict_to_dotdict(dct):
    """
    Given a dct formatted as a dictionary, returns an object
    that also supports "dot" access:

    dct['data']['child']
    dct.data.child
    """
    if not isinstance(dct, dict):
        return dct
    for key, value in list(dct.items()):
        if isinstance(value, dict):
            dct[key] = dict_to_dotdict(value)
        elif isinstance(value, list):
            dct[key] = [dict_to_dotdict(v) for v in value]
    return DotDict(dct)


class CompoundKey(tuple):
    pass


def dict_to_flatdict(dct, parent=None):
    """Converts a (nested) dictionary to a flattened representation.

    Each key
    of the flat dict will be a CompoundKey tuple containing the "chain of keys"
    for the corresponding value.

    Args:
        dct (dict): The dictionary to flatten
        parent (CompoundKey, optional): Defaults to None. The parent key
        (you shouldn't need to set this)

    """

    items = []
    parent = parent or CompoundKey()
    for k, v in dct.items():
        k_parent = CompoundKey(parent + (k,))
        if isinstance(v, dict):
            items.extend(dict_to_flatdict(v, parent=k_parent).items())
        else:
            items.append((k_parent, v))
    return dict(items)

def flatdict_to_dict(dct):
    """Converts a flattened dictionary back to a nested dictionary.

    Args:
        dct (dict): The dictionary to be nested. Each key should be a
        CompoundKey, as generated by dict_to_flatdict()

    """

    result = {}
    for k, v in dct.items():
        if isinstance(k, CompoundKey):
            current_dict = result
            for ki in k[:-1]:
                current_dict = current_dict.setdefault(ki, {})
            current_dict[k[-1]] = v
        else:
            result[k] = v

    return result