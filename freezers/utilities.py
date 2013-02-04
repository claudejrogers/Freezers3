_MASK = 0xFF
_SHIFTS = (32, 24, 16, 8, 0)


def getaddress(position):
    return sum(p << s for p, s in zip(position, _SHIFTS))


def getposition(address):
    return tuple((address >> s) & _MASK for s in _SHIFTS)


def get_bounding_addresses(containers, adjust_by=1):
    faddr = getaddress(containers)
    size = len(containers)
    if size == 5:
        laddr = (faddr - containers[-1]) + 0x0100
    else:
        laddr = faddr + (adjust_by << (8 * (5 - (size or 1))))
    return (faddr, laddr)
