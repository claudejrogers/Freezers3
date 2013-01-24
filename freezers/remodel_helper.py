from django.db import transaction
from freezers.models import *


class RemodelException(Exception):
    pass


@transaction.autocommit
def remodel_cells(fid, cur, new_box_capacity, new_box_width, faddress,
                  laddress, cur_max_address, new_max_address,
                  org_max_address):
    # if the new number of sample locations is less than the current number,
    # mark all the samples greater than the new capacity as occupied=None, if
    # none of these locations have samples in them. For the rest of the
    # samples, change occupancy to False if None and change box_width and
    # cell capacity to the new values.
    if new_max_address < cur_max_address:
        cur.execute("""SELECT ID FROM freezers_samplelocation
                       WHERE freezer_id = %s AND
                             address > %s AND
                             address < %s AND
                             occupied = True""",
                    (fid, new_max_address, laddress))
        occupied_sl = cur.fetchall()
        # check if there are samples in the to-be-nulled section of the box
        if occupied_sl:
            raise RemodelException, 'Move samples before remodeling.'
        # null the extra samples
        if cur_max_address > org_max_address:
            cur.execute("""UPDATE freezers_samplelocation
                               SET occupied = %s
                           WHERE freezer_id = %s AND
                                 address > %s AND
                                 address <= %s""",
                        (None, fid, new_max_address, org_max_address))
            transaction.commit()
            cur.execute("""DELETE FROM freezers_samplelocation
                           WHERE freezer_id = %s AND
                                 address > %s AND
                                 address < %s""",
                        (fid, max(org_max_address, new_max_address), laddress))
            transaction.commit()
        else:
            cur.execute("""UPDATE freezers_samplelocation
                               SET occupied = NULL
                           WHERE freezer_id = %s AND
                                 address > %s AND
                                 address < %s AND
                                 occupied IS NOT NULL""",
                        (fid, new_max_address, laddress))
            transaction.commit()
        # Change cell_capacity and box_width for all sample locations
        cur.execute("""UPDATE freezers_samplelocation
                           SET cell_capacity = %s,
                               box_width = %s
                       WHERE freezer_id = %s AND
                             address >= %s AND
                             address < %s""",
                    (new_box_capacity, new_box_width, fid, faddress, laddress))
        transaction.commit()
    # if the current non-null number of cells is less than the desired number
    # of cells, first check if there are null cells, convert them to
    # unoccupied
    elif new_max_address > cur_max_address:
        if max(org_max_address, cur_max_address) < new_max_address:
            # Need to create samples
            a1 = max(org_max_address, cur_max_address)+1
            attrs = [(False, fid, address, new_box_width, new_box_capacity)
                     for address in xrange(a1, new_max_address+1)]
            cur.executemany("""INSERT INTO freezers_samplelocation
                               (occupied, freezer_id, address, box_width,
                                cell_capacity) values (%s, %s, %s, %s, %s)""",
                            attrs)
            transaction.commit()
        # Null sample locations should become false, have correct attr
        cur.execute("""UPDATE freezers_samplelocation
                           SET occupied = %s,
                               cell_capacity = %s,
                               box_width = %s
                       WHERE freezer_id = %s AND
                             address >= %s AND
                             address <= %s AND
                             occupied IS NULL""",
                    (False, new_box_capacity, new_box_width, fid,
                     faddress, new_max_address))
        transaction.commit()
        # Non-null samples need to update attr
        cur.execute("""UPDATE freezers_samplelocation
                           SET cell_capacity = %s,
                               box_width = %s
                       WHERE freezer_id = %s AND
                             address >= %s AND
                             address <= %s AND
                             occupied IS NOT NULL""",
                    (new_box_capacity, new_box_width, fid,
                     faddress, new_max_address))
        transaction.commit()

def remodel_cells_in_freezer_subsection(new_value, box_dim, fid, sid,
                                        rid=None, did=None, bid=None):
    new_box_capacity = new_value
    new_box_width = box_dim
    f = Freezer.objects.get(pk=fid)
    cur = connection.cursor()

    # get all sample locations in this sublocation
    start_pos = map(int, [c or 1 for c in (sid, rid, did, bid, 1)])
    end_pos = list(start_pos)
    end_pos[len([c for c in (sid, rid, did, bid) if c]) - 1] += 1
    start_address = getaddress(start_pos)
    end_address = getaddress(end_pos)
    cur.execute("""SELECT address, occupied FROM freezers_samplelocation
                   WHERE freezer_id = %s AND
                         address >= %s AND
                         address < %s""",
                (fid, start_address, end_address))
    sl = cur.fetchall()
    locdict = {}
    for (address, occupied) in sl:
        box_address = address >> 8
        locdict[box_address] = max(locdict.get(box_address, 0),
            address if occupied is not None else 0)


    for k, v in locdict.iteritems():
        faddress = (k << 8) + 1
        laddress = (k << 8) + 0x101
        org_max_address = (k << 8) + f.cell_capacity
        new_max_address = (k << 8) + new_box_capacity
        cur_max_address = v
        remodel_cells(fid, cur, new_box_capacity, new_box_width, faddress,
                      laddress, cur_max_address, new_max_address,
                      org_max_address)

@transaction.autocommit
def make_default_box(f, sid, rid, did, bid):
    """
    Make a new, empty box in given location.
    """
    cur = connection.cursor()
    faddress = getaddress((sid, rid, did, bid, 1))
    laddress = getaddress((sid, rid, did, bid, f.cell_capacity+1))
    attrs = [(False, f.id, address, f.box_width, f.cell_capacity)
             for address in xrange(faddress, laddress)]
    cur.executemany("""INSERT INTO freezers_samplelocation (occupied,
        freezer_id, address, box_width, cell_capacity)
        values (%s, %s, %s, %s, %s)""", attrs)
    transaction.commit()

@transaction.autocommit
def make_default_box_1(f, cur, base_addr, bid):
    """
    Make a new, empty box in given location.
    """
    faddress = (base_addr << 16) + (bid << 8) + 1
    laddress = faddress + f.cell_capacity
    attrs = [(False, f.id, address, f.box_width, f.cell_capacity)
             for address in xrange(faddress, laddress)]
    cur.executemany("""INSERT INTO freezers_samplelocation (occupied,
        freezer_id, address, box_width, cell_capacity)
        values (%s, %s, %s, %s, %s)""", attrs)
    transaction.commit()

@transaction.autocommit
def remodel_boxes(fid, cur, new_drawer_capacity, base_address, box_ids,
                  laddress, new_max_address, org_max_address,
                  cur_max_address):
    f = Freezer.objects.get(pk=fid)
    cur_max_box = len(box_ids)
    if new_drawer_capacity < cur_max_box:
        # check if there are occupied sample locations
        cur.execute("""SELECT ID FROM freezers_samplelocation
            WHERE freezer_id = %s AND address >= %s and address < %s AND
            occupied = True""", (fid, new_max_address, laddress))
        occupied_sl = cur.fetchall()
        if occupied_sl:
            raise RemodelException, 'Move samples before remodeling.'
        if cur_max_box > f.box_capacity:
            cur.execute("""DELETE FROM freezers_samplelocation
                           WHERE freezer_id = %s AND
                                 address >= %s AND
                                 address < %s""",
                        (fid, max(org_max_address, new_max_address), laddress))
            transaction.commit()
            cur.execute("""UPDATE freezers_samplelocation
                               SET occupied = NULL
                           WHERE freezer_id = %s AND
                                 address >= %s AND
                                 address < %s""",
                        (fid, new_max_address, org_max_address))
            transaction.commit()
        else:
            cur.execute("""UPDATE freezers_samplelocation
                                SET occupied = NULL
                           WHERE freezer_id = %s AND
                                 address >= %s AND
                                 address < %s""",
                        (fid, new_max_address, laddress))
            transaction.commit()
    else:
        # create boxes as needed, make sure other boxes have at least one
        # non-null samplelocation
        for bid in range(cur_max_box+1, new_drawer_capacity+1):
            make_default_box_1(f, cur, base_address, bid)
        for bid in box_ids:
            fbaddress = (base_address << 16) + (bid << 8) + 1
            lbaddress = fbaddress + 0x0100
            cur.execute("""SELECT ID FROM freezers_samplelocation
                           WHERE freezer_id = %s AND
                                 address >= %s AND
                                 address < %s AND
                                 occupied IS NOT NULL""",
                        (fid, fbaddress, lbaddress))
            this_box = cur.fetchall()
            if not this_box: # box is all null
                cur.execute("""UPDATE freezer_samplelocation
                                   SET occupied = False,
                                       cell_capacity = %s,
                                       box_width = %s
                               WHERE freezer_id = %s AND
                                     address >= %s AND
                                     address < %s""",
                            (f.cell_capacity, f.box_width, fid, fbaddress,
                             lbaddress))
                transaction.commit()

def remodel_boxes_in_freezer_subsection(new_value, fid, sid, rid=None,
                                        did=None):
    new_drawer_capacity = new_value
    cur = connection.cursor()
    f = Freezer.objects.get(pk=fid)

    # get all sample locations in this sublocation
    start_pos = map(int, [c or 1 for c in (sid, rid, did, 1, 1)])
    end_pos = list(start_pos)
    end_pos[len([c for c in (sid, rid, did) if c]) - 1] += 1
    start_address = getaddress(start_pos)
    end_address = getaddress(end_pos)
    cur.execute("""SELECT address FROM freezers_samplelocation
                        WHERE freezer_id = %s AND
                              address >= %s AND
                              address < %s""",
                     (fid, start_address, end_address))
    sl = cur.fetchall()
    locdict = {}
    for (address,) in sl:
        srd = address >> 16
        locdict.setdefault(srd, set()).add(int((address >> 8) & 0xFF))

    for k, v in locdict.iteritems():
        base_address = k
        box_ids = sorted(v)
        laddress = (k << 16) + 0x010101
        new_max_address = (k << 16) + ((new_drawer_capacity + 1) << 8) + 1
        org_max_address = (k << 16) + ((f.box_capacity + 1) << 8) + 1
        cur_max_address = (k << 16) + ((len(box_ids) + 1) << 8) + 1
        remodel_boxes(fid, cur, new_drawer_capacity, base_address, box_ids,
                      laddress, new_max_address, org_max_address,
                      cur_max_address)

@transaction.autocommit
def remodel_drawers(fid, cur, new_rack_capacity, base_address, drawer_ids,
                    faddress, laddress, new_max_address, org_max_address,
                    cur_max_address):
    f = Freezer.objects.get(pk=fid)
    cur_max_drawers = len(drawer_ids)
    if new_rack_capacity < cur_max_drawers:
        cur.execute("""SELECT address FROM freezers_samplelocation WHERE
                       freezer_id = %s AND address >= %s AND address < %s""",
                    (fid, faddress, laddress))
        cur_max_address = max([address for (address,) in cur.fetchall()])
        if cur_max_address > org_max_address:
            cur.execute("""SELECT ID FROM freezers_samplelocation
                WHERE freezer_id = %s AND address >= %s AND address < %s AND
                occupied = True""",(fid, new_max_address, laddress))
            occupied_sl = cur.fetchall()
            if occupied_sl:
                raise RemodelException, 'Move samples before remodeling.'
            cur.execute("""UPDATE freezers_samplelocation
                               SET occupied = NULL
                           WHERE freezer_id = %s AND
                                 address >= %s AND
                                 address <= %s AND
                                 occupied IS NOT NULL""",
                        (fid, new_max_address, org_max_address))
            transaction.commit()
            cur.execute("""DELETE from freezers_samplelocation WHERE
                              freezer_id = %s AND
                              address >= %s AND
                              address < %s""",
                           (fid, max(org_max_address, new_max_address),
                            laddress))
            transaction.commit()
        else:
            cur.execute("""UPDATE freezers_samplelocation
                               SET occupied = NULL
                           WHERE freezer_id = %s AND
                                 address >= %s AND
                                 address < %s AND
                                 occupied IS NOT NULL""",
                        (fid, new_max_address, laddress))
            transaction.commit()
    else:
        for did in xrange(cur_max_drawers+1, new_rack_capacity+1):
            baddr = (base_address << 8) + did
            for bid in xrange(1, f.box_capacity+1):
                make_default_box_1(f, cur, baddr, bid)
        for did in drawer_ids:
            fdaddress = (base_address << 24) + (did << 16) + 0x0101
            ldaddress = fdaddress + 0x010000
            cur.execute("""SELECT address FROM freezers_samplelocation WHERE
                                  freezer_id = %s AND
                                  address >= %s AND
                                  address < %s AND
                           occupied IS NOT NULL""",
                        (fid, fdaddress, ldaddress))
            this_drawer = cur.fetchall()
            if not this_drawer:
                for bid in xrange(1, f.box_capacity+1):
                    fbaddress = (base_address << 24)+(did << 16)+(bid << 8)+1
                    lbaddress = fbaddress + 0x0100
                    cur.execute("""UPDATE freezers_samplelocation
                                       SET occupied = False,
                                           cell_capacity = %s,
                                           box_width = %s
                                   WHERE freezer_id = %s AND
                                         address >= %s AND
                                         address < %s AND
                                         occupied IS NULL""",
                                (f.cell_capacity, f.box_width, fid, faddress,
                                 lbaddress))
                    transaction.commit()


def remodel_drawers_in_freezer_subsection(new_value, fid, sid, rid=None):
    new_rack_capacity = new_value
    cur = connection.cursor()
    f = Freezer.objects.get(pk=fid)

    # get all sample locations in this sublocation
    start_pos = map(int, [c or 1 for c in (sid, rid, 1, 1, 1)])
    end_pos = list(start_pos)
    end_pos[len([c for c in (sid, rid) if c]) - 1] += 1
    start_address = getaddress(start_pos)
    end_address = getaddress(end_pos)
    cur.execute("""SELECT address FROM freezers_samplelocation
                        WHERE freezer_id = %s AND
                              address >= %s AND
                              address < %s""",
                     (fid, start_address, end_address))
    sl = cur.fetchall()
    locdict = {}
    for (address,) in sl:
        srd = address >> 24
        locdict.setdefault(srd, set()).add(int((address >> 16) & 0xFF))

    for k, v in locdict.iteritems():
        base_address = k
        drawer_ids = sorted(v)
        faddress = (k << 24) + 0x010101
        laddress = faddress + 0x01000000
        new_max_address = (k << 24) + ((new_rack_capacity + 1) << 16) + 0x0101
        org_max_address = (k << 24) + ((f.drawer_capacity + 1) << 16) + 0x0101
        cur_max_address = (k << 24) + ((len(drawer_ids) + 1) << 16) + 0x0101
        remodel_drawers(fid, cur, new_rack_capacity, base_address, drawer_ids,
                        faddress, laddress, new_max_address, org_max_address,
                        cur_max_address)

@transaction.autocommit
def remodel_racks_in_freezer_subsection(new_value, fid, sid):
    new_shelf_capacity = new_value
    f = Freezer.objects.get(pk=fid)
    faddress = getaddress((sid, 1, 1, 1, 1))
    laddress = getaddress((sid+1, 1, 1, 1, 1))
    cur = connection.cursor()
    cur.execute("""SELECT address FROM freezers_samplelocation WHERE
                        freezer_id = %s AND address >= %s AND address < %s""",
                     (fid, faddress, laddress))
    sl = cur.fetchall()
    rack_ids = list(set((address >> 24) & 0xFF for (address,) in sl))
    cur_max_racks = len(rack_ids)
    if new_shelf_capacity < cur_max_racks:
        new_max_address = getaddress((sid, new_shelf_capacity+1, 1, 1, 1))
        org_max_address = getaddress((sid, f.rack_capacity+1, 1, 1, 1))
        cur.execute("""SELECT address from freezers_samplelocation WHERE
                           freezer_id = %s AND address >= %s AND
                           address < %s""", (fid, faddress, laddress))
        cur_max_address = max([address for (address,) in cur.fetchall()])
        cur.execute("""SELECT ID FROM freezers_samplelocation
            WHERE freezer_id = %s AND address >= %s AND address < %s AND
            occupied = True""",(fid, new_max_address, laddress))
        occupied_sl = cur.fetchall()
        if occupied_sl:
            raise RemodelException, 'Move samples before remodeling.'
        if cur_max_address > org_max_address:
            cur.execute("""UPDATE freezers_samplelocation
                               SET occupied = NULL
                           WHERE freezer_id = %s AND
                                 address >= %s AND
                                 address <= %s AND
                                 occupied IS NOT NULL""",
                        (fid, new_max_address, org_max_address))
            transaction.commit()
            cur.execute("""DELETE from freezers_samplelocation WHERE
                               freezer_id = %s AND
                               address >= %s AND
                               address < %s""",
                        (fid, max(org_max_address, new_max_address),
                            laddress))
            transaction.commit()
        else:
            cur.execute("""UPDATE freezers_samplelocation
                               SET occupied = NULL
                           WHERE freezer_id = %s AND
                                 address >= %s AND
                                 address < %s AND
                                 occupied IS NOT NULL""",
                        (fid, new_max_address, laddress))
            transaction.commit()
    else:
        for rid in range(cur_max_racks+1, new_shelf_capacity+1):
            for did in range(1, f.drawer_capacity+1):
                for bid in range(1, f.box_capacity+1):
                    make_default_box(f, sid, rid, did, bid)
        for rid in rack_ids:
            fraddress = getaddress((sid, rid, 1, 1, 1))
            lraddress = getaddress((sid, rid+1, 1, 1, 1))
            cur.execute("""SELECT ID FROM freezers_samplelocation
                                       WHERE freezer_id = %s AND
                                             address >= %s AND
                                             address < %s AND
                                             occupied IS NOT NULL""",
                                    (fid, fraddress, lraddress))
            this_rack = cur.fetchall()
            if not this_rack:
                for did in range(1, f.drawer_capacity+1):
                    for bid in range(1, f.box_capacity+1):
                        fbaddress = getaddress((sid, rid, did, bid, 1))
                        lbaddress = getaddress((sid, rid, did, bid+1, 1))
                        cur.execute("""UPDATE freezers_samplelocation
                                           SET occupied = False
                                       WHERE freezer_id = %s AND
                                             address >= %s AND
                                             address < %s AND
                                             occupied IS NOT True""",
                                    (fid, fbaddress, lbaddress))
                        trasaction.commit()


