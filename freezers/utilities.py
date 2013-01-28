_MASK = 0xFF
_SHIFTS = (32, 24, 16, 8, 0)

def getaddress(position):
    return sum(p << s for p, s in zip(position, _SHIFTS))

def getposition(address):
    return tuple((address >> s) & _MASK for s in _SHIFTS)
