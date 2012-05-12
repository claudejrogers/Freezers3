_MASK = 0xFF
_SHIFTS = (32, 24, 16, 8, 0)

def getaddress(position):
    address = 0
    for i, p in enumerate(position):
        address += (p << _SHIFTS[i])
    return address

def getposition(address):
    position = []
    for s in _SHIFTS:
        position.append((address >> s) & _MASK)
    return tuple(position)
