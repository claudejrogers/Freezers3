import os
import codecs
from django.db import connection
from Freezers3.settings import MEDIA_ROOT, MEDIA_URL
from freezers.models import *
from freezers.utilities import getposition
from freezers.remodel_helper import *

def _freezer_filter(freezer, sn, rn=None, dn=None):
    if not rn:
        return sorted(set(r for (s,r,d,b) in freezer if s == sn))
    elif not dn:
        return sorted(set(d for (s,r,d,b) in freezer
                           if s == sn and r == rn))
    return sorted(set(b for (s,r,d,b) in freezer
                       if s == sn and r == rn and d == dn))

class FreezerHelper:
    def __init__(self, location_id, sublocation_list):
        self.location_id = location_id
        self.sublocation_list = sublocation_list

def freezerViewHelper(freezer_id):
    master = []
    c = connection.cursor()
    c.execute("""SELECT box_addr, name FROM freezers_boxname WHERE
                 freezer_id = %s""", (freezer_id,))
    names = dict(c.fetchall())
    c.execute("""SELECT address FROM freezers_samplelocation WHERE
                 freezer_id = %s AND occupied IS NOT NULL""", (freezer_id,))
    freezer = [map(int, (r, s, d, b)) for r, s, d, b, cell in
               [getposition(address[0]) for address in c.fetchall()]
               if cell == 1]
    for shelf in sorted(set(s for (s,r,d,b) in freezer)):
        rack_list = []
        for rack in _freezer_filter(freezer, shelf):
            drawer_list = []
            for drawer in _freezer_filter(freezer, shelf, rack):
                box_list = []
                for box in _freezer_filter(freezer, shelf, rack, drawer):
                    traddr = (shelf << 24) + (rack << 16) + (drawer << 8) + box
                    box_list.append(FreezerHelper(box, names.get(traddr, '')))
                drawer_item = FreezerHelper(drawer, box_list)
                drawer_list.append(drawer_item)
            rack_item = FreezerHelper(rack, drawer_list)
            rack_list.append(rack_item)
        shelf_item = FreezerHelper(shelf, rack_list)
        master.append(shelf_item)
    return master

class LocationHelper:
    def __init__(self, loc_id, index, link, width, capacity, occupied,
                 sample=None):
        self.loc_id = loc_id
        self.index = index
        self.link = link
        self.width = width
        self.capacity = capacity
        self.occupied_class = occupied
        self.name = sample.name if sample else None
        self.aliquot = sample.aliquot_number if sample else None

    def is_occupied(self):
        if self.occupied_class == "occupied_sample":
            return True
        return False

    def cell_location_name(self):
        c = chr(65 + ((self.index - 1) / self.width))
        x = self.index % self.width or self.width
        return u"%s%02d" % (c, x)

    def get_title_text(self):
        loc_name = self.cell_location_name()
        if self.link == "/freezers/samples/%d/" % self.loc_id:
            return (u"Edit/move/view sample\n"
                    u"\tname:    %s\n"
                    u"\taliquot: %d\n"
                    u"in Cell %s" % (self.name, self.aliquot, loc_name))
        elif "/move/" in self.link:
            return u"Move sample to Cell %s" % loc_name
        return u"EMPTY: Add sample to Cell %s" % loc_name

def getBoxContext(freezer_id, shelf_id, rack_id, drawer_id, box_id,
                  url_suffix, url_prefix='freezers'):
    # Get Sample locations for this box
    this_box = getaddress(map(int, (shelf_id, rack_id, drawer_id, box_id, 1)))
    next_box = this_box + 0x0100
    sl = SampleLocation.objects.filter(freezer=freezer_id,
                                       address__gte=this_box,
                                       address__lt=next_box).exclude(
                                       occupied=None).extra(
                                       order_by = ['address'])
    # an array to help javascript color sample locations
    slo = map(lambda x: 1 if x else 0, [s.occupied for s in sl])
    capacity = sl[0].cell_capacity
    width = max(sl[0].box_width, capacity / sl[0].box_width)
    # get sample list for sample table
    sample_list = sl.filter(occupied=True)
    occupied = []
    ml = []
    for i, s in enumerate(sl):
        v = s.id
        samp = None
        if slo[i]:
            occupied_class = "occupied_sample"
            link = "/freezers/samples/%d/" % v
            samp = s
        else:
            occupied_class = "unoccupied_sample"
            link = '/'.join(('', url_prefix, freezer_id,shelf_id, rack_id,
                             drawer_id, box_id, str(i + 1), url_suffix))
        if (i + 1) % width != 0:
            ml.append(LocationHelper(v, (i+1), link, width, capacity,
                                     occupied_class, sample=samp))
        else:
            ml.append(LocationHelper(v, (i+1), link, width, capacity,
                                     occupied_class, sample=samp))
            occupied.append(ml)
            ml = []
    context = {
        'slo': slo,
        'occupied': occupied,
        'samples': sample_list,
        'width': width
    }
    return context

def getSampleAliquots(s):
    s_aliquot_number = s.aliquot_number
    samples = [s]
    sa = SampleLocation.objects.filter(freezer=s.freezer.id, occupied=True,
                                       name=s.name, address__gt=s.address,
                                       aliquot_number__gt=s.aliquot_number)
    for i, samp in enumerate(sa, start=1):
        if samp.aliquot_number == s_aliquot_number + i:
            samples.append(samp)
    return samples

def getMoveSampleDisplay(s, samples=None):
    if not samples:
        samples = getSampleAliquots(s)
    bw = s.box_width
    cap = s.cell_capacity
    width = max(bw, cap/bw)
    display_list = []
    ml = []
    for i, s in enumerate(samples, start=1):
        ml.append({
            'text': "%s currently in %s" % (s.name, s.__unicode__()),
            'index': i
        })
        if i % width == 0:
            display_list.append(ml)
            ml = []
    if ml:
        display_list.append(ml)
    context = {
        'display_list': display_list,
        'alonum': len(samples)
    }
    return context

def getSampleList(index, fsl, nsamples):
    fsl = fsl.extra(order_by = ['address'])
    sample_list = [fsl[index]]
    try:
        for i in xrange(nsamples-1):
            current = fsl[index+i+1]
            prev = sample_list[i]
            cp = getposition(current.address)
            pp = getposition(prev.address)
            if pp[4] + 1 == cp[4]:
                sample_list.append(current)
            elif pp[3]+1 == cp[3] and pp[4] == prev.cell_capacity and cp[4] == 1:
                sample_list.append(current)
            else:
                return getSampleList(index+i+1, fsl, nsamples)
        return sample_list
    except IndexError:
        return []

def remodelFreezerHelper(field_to_change, new_value, fid, sid, rid=None,
                         did=None, bid=None, box_dim=None):
    l = locals()
    del l['field_to_change']
    args = dict([(k, v) for k, v in l.iteritems() if v])
    case = {
        'new_rack_capacity': remodel_racks_in_freezer_subsection,
        'new_drawer_capacity': remodel_drawers_in_freezer_subsection,
        'new_box_capacity': remodel_boxes_in_freezer_subsection,
        'new_cell_capacity': remodel_cells_in_freezer_subsection,
    }
    return case[field_to_change](**args)

class AbbrLocation:
    def __init__(self, freezer_id, addr):
        self.fid = freezer_id
        self.traddr = addr
        self.sid = (addr >> 24) & 0xFF
        self.rid = (addr >> 16) & 0xFF
        self.did = (addr >> 8) & 0xFF
        self.bid = addr & 0xFF
        self.name = self.get_box_name()

    def location(self):
        fname = Freezer.objects.get(pk=self.fid).__unicode__()
        return "%s Shelf %d Rack %d Drawer %d Box %d" % (fname, self.sid,
                                                         self.rid, self.did,
                                                         self.bid)
    def get_box_name(self):
        try:
            bn = BoxName.objects.get(freezer=self.fid, box_addr=self.traddr)
            return bn.name
        except:
            return ''

def searchHelper(s, query):
    """
    Further filter a list of sample/removed sample objects.

    s: A list of sample objects. For example,
       s = SampleLocation.objects.filter(occupied=True) or
       s = RemovedSample.objects.all()

    query: A list of search terms seperated by a space. For example,
           query = "Protein Laminin 2011"
           Optionally, a field can be specified using a key:value syntax,
           query = "type:protein name:laminin"
           this will limit the search to the requested keys.
    The function returns a list of hits common to all the terms in the query.
    """
    attrs = (
        'name__icontains',
        'date_added__icontains',
        'catalog_number__icontains',
        'production_date__icontains',
        'species__icontains',
        'host_cell_name__icontains',
        'date_removed__icontains'
    )
    attr_key = {
        'name': 'name__icontains',
        'da': 'date_added__icontains',
        'pd': 'production_date__icontains',
        'species': 'species__icontains',
        'hcn': 'host_cell_name__icontains',
        'catno': 'catalog_number__icontains',
    }
    qlist = query.split(' ')
    res = []
    for q in qlist:
        r = set()
        if len(q.split(':')) == 2:
            term, fkq = q.split(':')
            if term in attr_key:
                kwarg = {attr_key[term]: fkq}
                res.append(set(s.filter(**kwarg)))
                continue
            elif term == 'user':
                users = []
                users += User.objects.filter(first_name__icontains=fkq)
                users += User.objects.filter(last_name__icontains=fkq)
                for user in set(users):
                    r |= set(s.filter(user=user.id))
                res.append(r)
                continue
            elif term == 'type':
                sts = SampleType.objects.filter(sample_type__icontains=fkq)
                for st in sts:
                    r |= set(s.filter(sample_type=st.id))
                res.append(r)
                continue
            elif term == 'pils':
                pils = PILabSupplier.objects.filter(
                                            pi_lab_supplier__icontains=fkq)
                for pil in pils:
                    r |= set(s.filter(pi_lab_supplier=pil.id))
                res.append(r)
                continue
            else:
                q = fkq # who knows wtf the user did. Try our best below
        for attr in attrs:
            kwarg = {attr: q}
            r |= set(s.filter(**kwarg))
        pils = PILabSupplier.objects.filter(pi_lab_supplier__icontains=q)
        for pil in pils:
            r |= set(s.filter(pi_lab_supplier=pil.id))
        sts = SampleType.objects.filter(sample_type__icontains=q)
        for st in sts:
            r |= set(s.filter(sample_type=st.id))
        users = []
        users += User.objects.filter(first_name__icontains=q)
        users += User.objects.filter(last_name__icontains=q)
        for user in set(users):
            r |= set(s.filter(user=user.id))
        res.append(r)
    results = res.pop()
    for rset in res:
        results &= rset
    return sorted(results, key=lambda x: x.id)

def _get_loc(address, box_width, cell_capacity):
    pos = list(getposition(address))
    n = pos.pop()
    dim = int(box_width)
    total = int(cell_capacity)
    length = max(dim, total / dim)
    c = chr(65 + ((n - 1) / length))
    x = n % length or length
    pos.append("%s%02d" % (c, x))
    containers = ('Shelf', 'Rack', 'Drawer', 'Box', 'Cell')
    return ' '.join(map(lambda x: ' '.join(x), zip(containers, map(str, pos))))


def exportSampleHelper(user):
    dirname = os.path.join(MEDIA_ROOT, user.username)
    if not os.path.isdir(dirname):
        os.mkdir(dirname)

    cur = connection.cursor()
    get_name = lambda model, fid: model.objects.get(pk=fid).__unicode__()
    cur.execute('''SELECT name, freezer_id, address, box_width, cell_capacity,
                   aliquot_number, solvent, sample_type_id, species,
                   host_cell_name, pi_lab_supplier_id, date_added,
                   production_date, concentration, volume, comments
                   FROM freezers_samplelocation WHERE user_id = %s''',
                (user.id,))
    samples = cur.fetchall()

    filename = os.path.join(dirname, "%s_samples.txt" % user.first_name)

    lines = (
        '\t'.join(map(unicode, (name,
                 get_name(Freezer, freezer) + ': ' + _get_loc(address,
                                                              box_width,
                                                              cell_capacity),
                  aliquot_number, solvent, concentration, volume,
                  get_name(SampleType, sample_type), species, host_cell_name,
                  get_name(PILabSupplier, pi_lab_supplier), date_added,
                  production_date, comments)))+'\n'
        for (name, freezer, address, box_width, cell_capacity, aliquot_number,
             solvent, sample_type, species, host_cell_name, pi_lab_supplier,
             date_added, production_date, concentration, volume, comments)
        in samples
    )
    f = codecs.open(filename, 'w', 'utf-32')
    f.write('\t'.join(("Name|Location|Aliquot|Solvent|Conc.|Vol.|Sample type|"
                       "Species|Host Cell Name|Pi/Lab/Supplier|Date Added|"
                       "Production Date|comments\n").split('|')))
    f.writelines(lines)
    f.close()

def getUserFiles(user):
    dirname = os.path.join(MEDIA_ROOT, user.username)
    if os.path.isdir(dirname):
        files = [dict(zip(('url', 'filename'),
                          ('/'.join((MEDIA_URL+user.username, f)),
                           f)))
                 for f in os.listdir(dirname)
                 if f.endswith('.txt') or f.endswith('.png')]
        has_text = ([f for f in files if f['filename'].endswith('.txt')] != [])
    else:
        files = []
        has_text = False
    return files, has_text

def get_box_name_or_empty_string(fid, sid, rid, did, bid):
    traddr = (int(sid) << 24) + (int(rid) << 16) + (int(did) << 8) + int(bid)
    try:
        bn = BoxName.objects.get(freezer=fid, box_addr=traddr).name
    except BoxName.DoesNotExist:
        bn = ''
    return bn

