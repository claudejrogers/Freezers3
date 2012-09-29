from django.db import transaction
from django.db.models import F
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib.sessions.backends.db import SessionStore

from freezers.models import *
from freezers.forms import *
from freezers.view_helper import *


@login_required
def freezer_index(request):
    """
    List freezers in a table
    """
    add_samples = request.GET.get('orig', '')
    freezer_list = Freezer.objects.all()
    for f in freezer_list:
        f.calcOccupied()
    return render(request, 'freezers/freezer_index.html', locals())

@login_required
@transaction.autocommit
def add_freezer(request):
    """
    Basic form to add new freezers to the database.
    Samplelocations created with freezer.
    """
    if request.method == 'POST':
        form = FreezerForm(request.POST)
        if form.is_valid():
            form.save()
            # Log when user adds new freezer
            log_action(
                request.user.username, 
                "added freezer", 
                form.cleaned_data
            )
            return HttpResponseRedirect('/freezers/')
    else:
        form = FreezerForm()
    return render(request, 'freezers/add_freezer.html', locals())

@login_required
def select_sample_location(request, freezer_id):
    """
    For a selected freezer, print sublocations.
    """
    fid = freezer_id
    f = get_object_or_404(Freezer, pk=fid)
    fname = f.__unicode__()
    shelves = freezerViewHelper(freezer_id)
    return render(request, 'freezers/select_sample_location.html',
                  locals())

@login_required
def select_box_location(request, freezer_id, shelf_id, rack_id, drawer_id,
                        box_id):
    """
    This page does two things:
    1. provide a javascript-generated picture of the box contents
    2. provide a tabular list of samples in the box
    """
    f = get_object_or_404(Freezer, pk=freezer_id)
    fname = f.__unicode__()
    c = getBoxContext(freezer_id, shelf_id, rack_id, drawer_id, box_id,
                      "add-samples/")
    bn = get_box_name_or_empty_string(freezer_id, shelf_id, rack_id, drawer_id,
                                      box_id)
    c.update({
        'request': request,
        'fname': fname,
        'boxname': bn,
        'fid': freezer_id,
        'sid': shelf_id,
        'rid': rack_id,
        'did': drawer_id,
        'bid': box_id,
        'curr_samp': '0.1'
    })
    return render(request, 'freezers/select_box_location.html', c)

@login_required
def add_samples_to_freezer(request, freezer_id, shelf_id=None, rack_id=None,
                           drawer_id=None, box_id=None, cell_id=None):
    """
    Allow user to add sample to any free location in the freezer
    """
    # get items for template context
    containers = [c for c in (freezer_id, shelf_id, rack_id, drawer_id,
                              box_id) if c]
    f = get_object_or_404(Freezer, pk=freezer_id)
    fname = f.__unicode__()
    c = dict(zip(('fid', 'sid', 'rid', 'did', 'bid'), containers))
    c.update({'fname': fname,
              'request': request})

    if box_id: # display box
        bc = getBoxContext(freezer_id, shelf_id, rack_id, drawer_id, box_id,
                           "add-samples/")
        bn = get_box_name_or_empty_string(freezer_id, shelf_id, rack_id,
                                          drawer_id, box_id)
        bc['curr_samp'] = int(cell_id)
        bc['boxname'] = bn
        c.update(bc)
    if request.method == 'POST':
        form = AddSampleForm(request.POST)
        if form.is_valid():
            start_pos = [int(con or 1) for con in (shelf_id, rack_id,
                                                   drawer_id, box_id,
                                                   cell_id)]
            end_pos = list(start_pos)
            offset = len(containers) - 2 if len(containers) > 1 else 0
            end_pos[offset] += f.shelf_capacity if len(containers) == 1 else 1
            faddress = getaddress(start_pos)
            laddress = getaddress(end_pos)

            fsl = SampleLocation.objects.filter(freezer=freezer_id,
                                                occupied=False,
                                                address__gte=faddress,
                                                address__lt=laddress)
            n = int(form.cleaned_data['number_of_aliquots'])
            smp_lst = getSampleList(0, fsl, n)
            if not smp_lst:
                msg = "There is only enough space for %d sample(s) in this \
                       location." % len(fsl)
                form = AddSampleForm()
                c.update({'form': form, 'msg': msg})
                url = "/freezers/"
                for container in containers:
                    url += container + '/'
                if cell_id:
                    url += cell_id + '/'
                c['url'] = url + "add-samples/"
                return render(request, 'freezers/add_samples_to_freezer.html',
                              c)
            first_address = smp_lst[0].address
            last_address = smp_lst[-1].address
            first_aliquot = (int(first_address)
                             - int(form.cleaned_data['starting_aliquot_number']))
            SampleLocation.objects.filter(
                freezer=freezer_id,
                address__gte=first_address,
                address__lte=last_address
            ).update(
                occupied=True,
                date_removed=None,
                name=form.cleaned_data['name'],
                aliquot_number=F('address') - first_aliquot,
                solvent=form.cleaned_data['solvent'],
                sample_type=form.cleaned_data['sample_type'],
                species=form.cleaned_data['species'],
                host_cell_name=form.cleaned_data['host_cell_name'],
                user=form.cleaned_data['user'],
                pi_lab_supplier=form.cleaned_data['pi_lab_supplier'],
                catalog_number=form.cleaned_data['catalog_number'],
                date_added=form.cleaned_data['date_added'],
                production_date=form.cleaned_data['production_date'],
                concentration=form.cleaned_data['concentration'],
                volume=form.cleaned_data['volume'],
                comments=form.cleaned_data['comments'])
            redirect_url = "/freezers/"
            for container in containers:
                redirect_url += container + '/'
            redirect_url += 'samples/' if len(containers) < 5 else ''
            # Log whenever a user adds a sample
            log_action(
                request.user.username,
                "added samples in addresses %s to %s" % (hex(first_address), 
                                                         hex(last_address)),
                form.cleaned_data
            )
            return HttpResponseRedirect(redirect_url)
    else:
        form = AddSampleForm()
    c['form'] = form
    url = "/freezers/"
    for container in containers:
        url += container + '/'
    if cell_id:
        url += cell_id + '/'
    c['url'] = url + "add-samples/"
    return render(request, 'freezers/add_samples_to_freezer.html', c)

@login_required
def sample_index_by_location(request, freezer_id, shelf_id=None,
                             rack_id=None, drawer_id=None):
    """
    List samples for a given freezer by specific location.
    """
    query = request.GET.get('query', '')
    msg, querystring = '', ''
    f = get_object_or_404(Freezer, pk=freezer_id)
    fname = f.__unicode__()
    containers = [c for c in (shelf_id, rack_id, drawer_id) if c]
    start_pos = [int(c or 1) for c in (shelf_id, rack_id, drawer_id, 1,
                                       1)]
    first_address = getaddress(start_pos)
    end_pos = list(start_pos)
    end_pos[len(containers)-1 if containers else 0] += 1
    end_address = getaddress(end_pos)
    if containers:
        s = SampleLocation.objects.filter(freezer=freezer_id,
                                          occupied=True,
                                          address__gte=first_address,
                                          address__lt=end_address)
    else: # user wants to see all samples in freezer
        s = SampleLocation.objects.filter(freezer=freezer_id,
                                          occupied=True)
    if query:
        sample_list = searchHelper(s, query)
        querystring = '&query=%s' % query.replace(' ', '+')
        if not sample_list:
            msg = 'No hits for %s' % query
            sample_list = s
    else:
        sample_list = s
    if request.method == 'POST':
        redirect_url = '/freezers/%s/' % freezer_id
        if containers:
            redirect_url += '/'.join(containers) + '/'
        redirect_url += 'samples/'
        form = SimpleSearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['search'].strip()
            redirect_url += '?query=%s' % query.replace(' ', '+')
            return HttpResponseRedirect(redirect_url)
        else:
            return HttpResponseRedirect(redirect_url)
    else:
        form = SimpleSearchForm()
    paginator = Paginator(sample_list, 50)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        samples = paginator.page(page)
    except (EmptyPage, InvalidPage):
        samples = paginator.page(paginator.num_pages)
    c = {
        'request': request,
        'samples': samples,
        'freezer': fname,
        'shelf': shelf_id,
        'rack': rack_id,
        'drawer': drawer_id,
        'form': form
    }
    if msg:
        c['msg'] = msg
    if querystring:
        c['querystring'] = querystring
    return render(request, 'freezers/sample_index_by_location.html', c)

@login_required
def sample_index(request):
    """
    Return a paginated list of all samples in database
    """
    msg, querystring = '', ''
    query = request.GET.get('query', '')
    s = SampleLocation.objects.filter(occupied=True)
    if query:
        querystring = '&query=%s' % query.replace(' ', '+')
        sample_list = searchHelper(s, query)
        if not sample_list:
            sample_list = s
            msg = "No hits for %s" % query
    else:
        sample_list = s
    if request.method == 'POST':
        redirect_url = '/freezers/samples/'
        form = SimpleSearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['search'].strip()
            redirect_url += '?query=%s' % query.replace(' ', '+')
            return HttpResponseRedirect(redirect_url)
        return HttpResponseRedirect(redirect_url)
    form = SimpleSearchForm()
    paginator = Paginator(sample_list, 50)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        samples = paginator.page(page)
    except (EmptyPage, InvalidPage):
        samples = paginator.page(paginator.num_pages)
    c = {
        'request': request,
        'samples': samples,
        'form': form
    }
    if msg:
        c['msg'] = msg
    if querystring:
        c['querystring'] = querystring
    return render(request, 'freezers/sample_index.html', c)

@login_required
def add_supplier(request):
    """
    Form to add a PILabSupplier
    """
    redirect_to = request.GET.get('next', '/freezers/')
    if request.method == 'POST':
        form = PILabSupplierForm(request.POST)
        if form.is_valid():
            form.save()
            # Log when user adds new supplier
            log_action(
                request.user.username, 
                "added new supplier", 
                form.cleaned_data
            )
            return HttpResponseRedirect(redirect_to)
    else:
        form = PILabSupplierForm()
    return render(request, 'freezers/add_supplier.html', locals())

@login_required
def supplier_index(request):
    """
    List PILabSupplier Objects
    """
    suppliers_list = PILabSupplier.objects.all()
    return render(request, 'freezers/supplier_index.html',
                  locals())

@login_required
def add_sample_type(request):
    """
    Form to add new sample types
    """
    redirect_to = request.GET.get('next', '/freezers/')
    if request.method == 'POST':
        form = SampleTypeForm(request.POST)
        if form.is_valid():
            form.save()
            # Log when user adds new sample type
            log_action(
                request.user.username, 
                "added new sample type", 
                form.cleaned_data
            )
            return HttpResponseRedirect(redirect_to)
    else:
        form = SampleTypeForm()
    return render(request, 'freezers/add_sample_type.html',
                  locals())

@login_required
def freezer_detail(request, freezer_id):
    """
    List the details for a freezer
    """
    f = get_object_or_404(Freezer, pk=freezer_id)
    return render(request, 'freezers/freezer_detail.html', locals())

@login_required
def supplier_detail(request, supplier_id):
    """
    List PI/Lab/Supplier details
    """
    supp = get_object_or_404(PILabSupplier, pk=supplier_id)
    return render(request, 'freezers/supplier_detail.html', locals())

@login_required
def sample_detail(request, sample_id):
    """
    List sample details
    """
    s = get_object_or_404(SampleLocation, pk=sample_id)
    if not s.occupied: # s is a location but doesn't have sample info
        raise Http404
    c = {
        'request': request,
        'sample': s,
        'fid': s.freezer.id,
    }
    c.update(dict(zip(('sid', 'rid', 'did', 'bid', 'cid'),
                      getposition(s.address))))
    return render(request, 'freezers/sample_detail.html', c)

@login_required
def edit_freezer(request, freezer_id):
    """
    Edit Freezer details
    """
    f = get_object_or_404(Freezer, pk=freezer_id)
    if request.method == 'POST':
        # show current attributes in form
        form = FreezerEditForm(request.POST, instance=f)
        if form.is_valid():
            f.building_room_number = form.cleaned_data['building_room_number']
            f.kind = form.cleaned_data['kind']
            f.model = form.cleaned_data['model']
            f.manufacturer = form.cleaned_data['manufacturer']
            f.product_number = form.cleaned_data['product_number']
            f.serial_number = form.cleaned_data['serial_number']
            f.phone_number = form.cleaned_data['phone_number']
            f.attrsave()
            # Log when user changes freezer details
            log_action(
                request.user.username, 
                "edited freezer %s" % freezer_id, 
                form.cleaned_data
            )
            return HttpResponseRedirect('/freezers/%s/' % freezer_id)
    else:
        form = FreezerEditForm(instance=f)
    return render(request, 'freezers/edit_freezer.html',
                  locals())

@login_required
def edit_supplier(request, supplier_id):
    supplier = get_object_or_404(PILabSupplier, pk=supplier_id)
    if request.method == 'POST':
        form = PILabSupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            # Log when user edits supplier
            log_action(
                request.user.username,
                "edited supplier",
                form.cleaned_data
            )
            return HttpResponseRedirect('/freezers/suppliers/%s/' % supplier_id)
    else:
        form = PILabSupplierForm(instance=supplier)
    return render(request, 'freezers/edit_supplier.html',
                  locals())

@login_required
def edit_sample(request, sample_id):
    """
    Edit samples, edit groups of related samples (aliquots).
    """
    s = get_object_or_404(SampleLocation, pk=sample_id)
    oldname = s.name
    if not s.occupied:
        raise Http404
    if request.method == 'POST':
        form = EditSampleForm(request.POST, instance=s)
        msgform = MessageForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['apply_to_aliquots']:
                r, sh, d, b, c = getposition(s.address)
                next_address = getaddress((r, sh, d+2, 1, 1))
                samples = SampleLocation.objects.filter(
                                        occupied=True,
                                        name=oldname,
                                        freezer=s.freezer.id,
                                        address__gt=s.address,
                                        address__lt=next_address,
                                        aliquot_number__gt=s.aliquot_number)
                for i, samp in enumerate(samples, start=1):
                    if samp.aliquot_number == s.aliquot_number + i:
                        samp.name = form.cleaned_data['name']
                        samp.aliquot_number = form.cleaned_data['aliquot_number']+i
                        samp.solvent = form.cleaned_data['solvent']
                        samp.species = form.cleaned_data['species']
                        samp.user = form.cleaned_data['user']
                        samp.pi_lab_supplier = form.cleaned_data['pi_lab_supplier']
                        samp.catalog_number = form.cleaned_data['catalog_number']
                        samp.date_added = form.cleaned_data['date_added']
                        samp.date_removed = form.cleaned_data['date_removed']
                        samp.production_date = form.cleaned_data['production_date']
                        samp.concentration = form.cleaned_data['concentration']
                        samp.volume = form.cleaned_data['volume']
                        samp.comments = form.cleaned_data['comments']
                        samp.save()
                        if form.cleaned_data['remove']:
                            samp.remove_sample()
            form.save()
            # Log when user edits samples
            log_action(
                request.user.username,
                "edited %d samples" % i,
                form.cleaned_data
            )
            if msgform.is_valid():
                if msgform.cleaned_data['send_message']:
                    msgargs = {
                        'subject': msgform.cleaned_data['subject'],
                        'message': msgform.cleaned_data['message'],
                        'sender': request.user,
                        'receiver': s.user,
                        'sample': s
                    }
                    m = Message(**msgargs)
                    m.save()
            if form.cleaned_data['remove']:
                s.remove_sample()
                return HttpResponseRedirect('/freezers/removed/')
            return HttpResponseRedirect('/freezers/samples/%s/' % sample_id)
    else:
        form = EditSampleForm(instance=s)
        form.fields["sample_type"].queryset = SampleType.objects.order_by('sample_type')
        form.fields["user"].queryset = User.objects.order_by('username')
        form.fields["pi_lab_supplier"].queryset = PILabSupplier.objects.order_by(
                                                            'pi_lab_supplier',
                                                            'organization')
        msgform = MessageForm()
    return render(request, 'freezers/edit_sample.html',
                  {'request': request, 'form': form, 'sid': sample_id, 'msgform': msgform})

@login_required
def move_sample_select_freezer(request, sample_id, msg=None):
    """
    Select a location to move sample into.
    First, select a freezer, then click a sublocation in the freezer
    """
    s = get_object_or_404(SampleLocation, pk=sample_id)
    c = getMoveSampleDisplay(s)
    c.update({'sid': sample_id, 'sample': s, 'request': request})
    if not s.occupied:
        raise Http404
    if request.method == 'POST':
        form = MoveSampleForm(request.POST)
        if form.is_valid():
            freezer_id = form.cleaned_data['select_freezer'].id
            atoa = 1 if form.cleaned_data['apply_to_aliquots'] else 0
            f = get_object_or_404(Freezer, pk=freezer_id)
            fname = f.__unicode__()
            shelves = freezerViewHelper(freezer_id)
            c.update({
                'form': form,
                'fid': freezer_id,
                'fname': fname,
                'shelves': shelves,
                'atoa': atoa
            })
            return render(request, 'freezers/move_sample.html', c)
        c['form'] = form
    else:
        form = MoveSampleForm()
        c['form'] = form
    return render(request, 'freezers/move_sample.html', c)

@login_required
def move_sample(request, sample_id, freezer_id, shelf_id=None, rack_id=None,
                drawer_id=None, box_id=None, cell_id=None, atoa='0'):
    """
    Moves the sample. If the user selects a box, show box contentents and
    allow user to select a cell to put the sample(s).
    Redirect user to location containing moved sample.
    """
    s = SampleLocation.objects.get(pk=sample_id)
    if box_id and not cell_id:
        # Show user the selected box, prompt user to select a cell_ID
        f = get_object_or_404(Freezer, pk=freezer_id)
        c = getBoxContext(freezer_id, shelf_id, rack_id, drawer_id, box_id,
                          "move/%s/" % atoa, 'freezers/samples/%s' % sample_id)
        bn = get_box_name_or_empty_string(freezer_id, shelf_id, rack_id,
                                          drawer_id, box_id)
        c.update(getMoveSampleDisplay(s))
        c.update({
            'request': request,
            'sample_id': sample_id,
            'sample': s,
            'fname': f.__unicode__(),
            'boxname': bn,
            'fid': freezer_id,
            'sid': shelf_id,
            'rid': rack_id,
            'did': drawer_id,
            'bid': box_id,
            'curr_samp': '0.1',
            'atoa': atoa
        })
        return render(request, 'freezers/move_sample_in_box.html', c)
    containers = [c for c in (shelf_id, rack_id, drawer_id,
                              box_id, cell_id) if c]
    start_pos = [int(x or 1) for x in (shelf_id, rack_id, drawer_id, box_id,
                                       cell_id)]
    first_address = getaddress(start_pos)
    end_pos = list(start_pos)
    index = len(containers)-1 if containers else 0
    if index > 3:
        # If a box is selected, the range should extend to the end of the box
        end_pos[3] += 1
        end_pos[4] = 1
    elif containers:
        end_pos[index] += 1
    else: # move to anywhere in freezer
        end_pos[index] += f.shelf_capacity
    end_address = getaddress(end_pos)
    fll = SampleLocation.objects.filter(freezer=freezer_id,
                                        occupied=False,
                                        address__gte=first_address,
                                        address__lt=end_address)
    samples = getSampleAliquots(s) if int(atoa) else [s]
    n = len(samples)
    loc_list = getSampleList(0, fll, n)
    if not loc_list:
        f = get_object_or_404(Freezer, pk=freezer_id)
        fname = f.__unicode__()
        lname = " ".join([" ".join(p) for p in zip(
                                ("shelf rack drawer box".split(" ")),
                                (shelf_id, rack_id, drawer_id, box_id))])
        if cell_id:
            flobj = SampleLocation.objects.filter(freezer=freezer_id,
                                                  address=first_address)[0]
            if int(atoa):
                lname += " starting at"
            lname +=" cell %s" % flobj.cell_location_name()
        msg = "Error: Not enough room in %s %s. Please select another location" % (
                    fname, lname)
        form = MoveSampleForm()
        c = {'form': form, 'sid': sample_id, 'msg': msg}
        return render(request, 'freezers/move_sample.html', c)
    for i, samp in enumerate(samples):
        samp.move(loc_list[i])
    redirect_url = '/freezers/%s/' % freezer_id
    if len(containers) == 5:
        containers = containers[:4]
    for container in containers:
        redirect_url += container + '/'
    if not box_id:
        redirect_url += 'samples/'
    return HttpResponseRedirect(redirect_url)

@login_required
def move_box_select_freezer(request, freezer_id, shelf_id, rack_id, drawer_id,
                            box_id):
    of = get_object_or_404(Freezer, pk=freezer_id)
    origin = "%s: Shelf %s Rack %s Drawer %s Box %s" % (of.__unicode__(),
                                                        shelf_id, rack_id,
                                                        drawer_id, box_id)
    c = getBoxContext(freezer_id, shelf_id, rack_id, drawer_id, box_id,
                      "#/")
    bn = get_box_name_or_empty_string(freezer_id, shelf_id, rack_id, drawer_id,
                                      box_id)
    c.update({'fr': freezer_id, 'sh': shelf_id, 'ra': rack_id, 'dr': drawer_id,
              'bo': box_id, 'origin': origin, 'curr_samp': '0.1',
              'boxname': bn, 'request': request})
    if request.method == 'POST':
        form = MoveBoxForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data['select_freezer']
            fid = f.id
            fname = f.__unicode__()
            shelves = freezerViewHelper(fid)
            box_address = getaddress(map(int, (freezer_id, shelf_id, rack_id,
                                               drawer_id, box_id)))
            c.update({
                'form': form,
                'fid': fid,
                'fname': fname,
                'shelves': shelves,
                'bad': box_address,
            })
            return render(request, 'freezers/move_box.html', c)
        c['form'] = form
    else:
        form = MoveBoxForm()
        c.update({'form': form})
    return render(request, 'freezers/move_box.html', c)

@login_required
def move_box(request, box_address, freezer_id, shelf_id, rack_id, drawer_id,
             box_id):
    box_address = int(box_address)
    redirect_url = '/'.join(('', 'freezers', freezer_id, shelf_id, rack_id,
                            drawer_id, box_id, ''))
    # get the contents of the box to be moved
    fid = (box_address >> 32) & 0xFF
    base_address = (box_address & 0xFFFFFFFF) << 8
    faddress = base_address + 0x01
    laddress = faddress + 0x0100
    ms = SampleLocation.objects.filter(freezer=fid,
                                       address__gte=faddress,
                                       address__lt=laddress)
    msdict = dict((s.address & 0xFF, s) for s in ms if s.occupied)

    tbaddr = getaddress(map(int, (shelf_id, rack_id, drawer_id, box_id, 0)))
    ftaddr = tbaddr + 1
    ltaddr = ftaddr + 0x0100
    ts = SampleLocation.objects.filter(freezer=freezer_id,
                                       address__gte=ftaddr, address__lt=ltaddr)
    remodel_flag = 0 if ms.count() == ts.count() else 1
    tsdict = {}
    for s in ts:
        if s.occupied:
            tsdict[s.address & 0xFF] = {
                'name': s.name,
                'sample_type': s.sample_type,
                'user': s.user,
                'pi_lab_supplier': s.pi_lab_supplier,
                'date_added': s.date_added,
                'production_date': s.production_date,
                'concentration': s.concentration,
                'volume': s.volume,
                'aliquot_number': s.aliquot_number,
                'solvent': s.solvent,
                'species': s.species,
                'host_cell_name': s.host_cell_name,
                'catalog_number': s.catalog_number,
                'date_removed': s.date_removed,
                'comments': s.comments
            }
            s.clearsample()
        if not remodel_flag:
            cell = s.address & 0xFF
            if cell in msdict:
                msdict[cell].move(s)

    if remodel_flag:
        mcap = ms[0].cell_capacity
        mdim = ms[0].box_width
        tcap = ts[0].cell_capacity
        tdim = ts[0].box_width
        remodelFreezerHelper('new_cell_capacity', mcap, int(freezer_id),
                             int(shelf_id), int(rack_id), int(drawer_id),
                             int(box_id), mdim)

        ts = SampleLocation.objects.filter(freezer=freezer_id,
                                           address__gte=ftaddr,
                                           address__lt=ltaddr)
        for s in ts:
            cell = s.address & 0xFF
            if cell in msdict:
                msdict[cell].move(s)

        fr, sh, dr, ra, bo = getposition(box_address)
        remodelFreezerHelper('new_cell_capacity', tcap, fr, sh, dr, ra, bo,
                             tdim)
        ms = SampleLocation.objects.filter(freezer=fid,
                                           address__gte=faddress,
                                           address__lt=laddress)
    for s in ms:
        cell = s.address & 0xFF
        if cell in tsdict:
            s.addsample(**tsdict[cell])
    try:
        bn = BoxName.objects.get(freezer=fid, box_addr=(base_address >> 8))
    except BoxName.DoesNotExist, e:
        bn = None
    try:
        nbn = BoxName.objects.get(freezer=freezer_id, box_addr=(tbaddr >> 8))
    except BoxName.DoesNotExist, e:
        nbn = None
    if bn and nbn:
        bn.name, nbn.name = nbn.name, bn.name
        bn.save()
        nbn.save()
    elif bn:
        name = bn.name
        f = Freezer.objects.get(pk=freezer_id)
        nbn = BoxName(freezer=f, box_addr=(tbaddr >> 8), name=name)
        nbn.save()
        bn.delete()
    elif nbn:
        name = nbn.name
        f = Freezer.objects.get(pk=fid)
        bn = BoxName(freezer=f, box_addr=(base_address >> 8), name=name)
        bn.save()
        nbn.delete()
    return HttpResponseRedirect(redirect_url)

##############################################################################

@login_required
def search(request, option=None, query=None):
    """
    Search samples based on fields.
    Return results as paginated list with the search form.
    """
    query = request.GET.get('query', '')
    msg, querystring = '', ''
    c = {}
    if request.method == 'POST':
        form = HeaderSearchForm(request.POST)
        redirect_url = '/freezers/search/'
        if form.is_valid():
            print "Is VALID!!!!"
            query = form.cleaned_data['header_search'].strip()
            redirect_url += '?query=%s' % query.replace(' ', '+')
            return HttpResponseRedirect(redirect_url)
    if query:
        s = SampleLocation.objects.filter(occupied=True)
        results = searchHelper(s, query)
        querystring = '&query=%s' % query.replace(' ', '+')
        if not results:
            results = None
        # Paginate
        if results:
            paginator = Paginator(results, 50)
            try:
                page = int(request.GET.get('page', '1'))
            except ValueError:
                page = 1
            try:
                res = paginator.page(page)
            except (EmptyPage, InvalidPage):
                res = paginator.page(paginator.num_pages)
            c['results'] = res
        else:
            msg = "Query resulted in no hits!"
            c['msg'] = msg
            print msg
    if querystring:
        c['querystring'] = querystring
    return render(request, 'freezers/search_samples.html', c)

##############################################################################

@login_required
def select_region_to_edit(request, freezer_id):
    f = Freezer.objects.get(pk=freezer_id)
    fname = f.__unicode__()
    shelves = freezerViewHelper(freezer_id)
    return render(request, 'freezers/select_region_to_edit.html', locals())

@login_required
def edit_freezer_region(request, freezer_id, shelf_id, rack_id=None,
                        drawer_id=None, box_id=None):
    """
    Allow users to customize the layout of the freezer.
    """
    f = get_object_or_404(Freezer, pk=freezer_id)
    fname = f.__unicode__()
    c = dict(zip(('fname', 'fid', 'sid', 'rid', 'did', 'bib'),
                  (fname, freezer_id, shelf_id, rack_id, drawer_id, box_id)))
    if request.method == 'POST':
        form = ChangeFreezerLayout(request.POST)
        if form.is_valid():
            msg = ''
            field_to_change = form.cleaned_data['change']
            new_value = form.cleaned_data['new_capacity']
            box_dim = form.cleaned_data['new_box_width']
            opts = ['new_rack_capacity', 'new_drawer_capacity',
                    'new_box_capacity']
            if rack_id and field_to_change in opts[0]:
                msg = "Invalid choice. \
                       You must select a sublocation of this rack."
            elif drawer_id and field_to_change in opts[:2]:
                msg = "Invalid choice. \
                       You must select a sublocation of this drawer."
            elif box_id and field_to_change in opts:
                msg = "Invalid choice. \
                       You must select a sublocation of this box."
            else:
                loc_ids = map(lambda x: int(x) if x else None,
                              (freezer_id, shelf_id, rack_id, drawer_id,
                               box_id))
                try:
                    remodelFreezerHelper(field_to_change, new_value,
                                         *loc_ids, box_dim=box_dim)
                    return HttpResponseRedirect(
                        '/freezers/%s/select-sample-location/' % freezer_id)
                except RemodelException, e:
                    msg = e
            if msg:
                c['msg'] = msg
    else:
        form = ChangeFreezerLayout()
    c.update({'form': form, 'request': request})
    return render(request, 'freezers/remodel_freezer.html', c)

@login_required
def removed_index(request, query=None):
    msg = ''
    return_code = request.GET.get('return', '')
    removed_id = request.GET.get('id', '')
    if request.method == 'POST':
        form = SimpleSearchForm(request.POST)
        if form.is_valid():
            return HttpResponseRedirect(
                '/freezers/removed/%(search)s/' % form.cleaned_data)
        else:
            results = RemovedSample.objects.all()
    else:
        form = SimpleSearchForm()
        if query:
            results = []
            attrs = (
                'name',
                'date_added',
                'production_date',
                'species',
                'host_cell_name',
                'date_removed'
            )
            for attr in attrs:
                kwarg = {attr+'__icontains': query}
                q = RemovedSample.objects.filter(**kwarg)
                results += q
            pils = PILabSupplier.objects.filter(pi_lab_supplier__icontains=query)
            for pil in pils:
                results += RemovedSample.objects.filter(
                                                pi_lab_supplier=pil.id)
            sts = SampleType.objects.filter(sample_type__icontains=query)
            for st in sts:
                results += RemovedSample.objects.filter(
                                                sample_type=st.id)
            name = query.split(' ')
            users = []
            for part in name:
                users += User.objects.filter(first_name__icontains=part)
                users += User.objects.filter(last_name__icontains=part)
            users = list(set(users))
            for user in users:
                results += RemovedSample.objects.filter(user=user.id)
            results = sorted(set(results), key=lambda x: x.id)
            if not results:
                msg = 'Query resulted in no hits.'
        else:
            results = RemovedSample.objects.all()
            if not results.exists():
                msg = 'No removed samples yet.'
    paginator = Paginator(results, 50)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        res = paginator.page(page)
    except (EmptyPage, InvalidPage):
        res = paginator.page(paginator.num_pages)
    c = {'request': request, 
         'return_code': return_code,
         'form': form, 
         'msg': msg, 
         'query': query, 
         'results': res}
    return render(request, 'freezers/removed_index.html', c)

@login_required
def removed_detail(request, removed_id):
    s = get_object_or_404(RemovedSample, pk=removed_id)
    return render(request, 'freezers/removed_detail.html', locals())

@login_required
def home_link(request):
    return redirect('/freezers/home/%s/' % request.user.id)

@login_required
def homepage(request, user_id):
    """
    User's homepage.
    """
    user = get_object_or_404(User, pk=user_id)
    if request.user != user:
        return redirect('/freezers/home/%s/' % request.user.id)
    query = request.GET.get('query', '')
    msg, querystring = '', ''
    s = SampleLocation.objects.filter(user=user)
    if query:
        querystring = '&query=%s' % query.replace(' ', '+')
        samples = searchHelper(s, query)
        if not samples:
            samples = s
            msg = "No hits for %s" % query
    else:
        samples = s
    messages = Message.objects.filter(receiver=user).order_by('-date')
    files, has_text = getUserFiles(user)
    cur = connection.cursor()
    cur.execute("""SELECT freezer_id, address
                         FROM freezers_samplelocation
                         WHERE user_id = %s""", (user_id,))
    sl = cur.fetchall()
    sls = sorted(set((a, b >> 8) for (a, b) in sl))
    locs = [AbbrLocation(*tup) for tup in sls]
    if request.method == 'POST':
        form = SimpleSearchForm(request.POST)
        redirect_url = '/freezers/home/%s/' % request.user.id
        if form.is_valid():
            query = form.cleaned_data['search'].strip()
            redirect_url += '?query=%s' % query.replace(' ', '+')
            return HttpResponseRedirect(redirect_url)
        else:
            return HttpResponseRedirect(redirect_url)
    form = SimpleSearchForm()
    paginator = Paginator(samples, 10)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        samp = paginator.page(page)
    except (EmptyPage, InvalidPage):
        samp = paginator.page(paginator.num_pages)
    c = {
        'user': user,
        'request': request,
        'locations': locs,
        'files': files,
        'has_text': has_text,
        'form': form,
        'samples': samp,
        'messages': messages
    }
    if msg:
        c['msg'] = msg
    if querystring:
        c['querystring'] = querystring
    return render(request, 'freezers/homepage.html', c)

@login_required
def delete_message(request, msg_id):
    m = get_object_or_404(Message, pk=msg_id)
    if m.receiver == request.user:
        m.delete()
    return HttpResponseRedirect('/freezers/home/%s/' % request.user.id)

@login_required
def reply_to_message(request, msg_id):
    m = get_object_or_404(Message, pk=msg_id)
    old_sender = m.sender
    samp = m.sample
    m.subject = 'RE: ' + m.subject
    m.message = '\n\n' + '-'*10 + '\n' + m.message
    if m.receiver != request.user:
        return HttpResponseRedirect('/freezers/home/%s/' % request.user.id)
    if request.method == 'POST':
        form = MessageForm(request.POST, instance=m)
        if form.is_valid() and form.cleaned_data['send_message']:
            msgargs = {
                'subject': form.cleaned_data['subject'],
                'message': form.cleaned_data['message'],
                'sender': request.user,
                'receiver': old_sender,
                'sample': samp
            }
            m = Message(**msgargs)
            m.save()
        return HttpResponseRedirect('/freezers/home/%s/' % request.user.id)
    else:
        form = MessageForm(instance=m)
    return render(request, 'freezers/reply_to_message.html',
                  {'request': request, 'form': form, 'msg_id': msg_id})

@login_required
def rearrange_samples_within_box(request, freezer_id, shelf_id, rack_id,
                                 drawer_id, box_id):
    """
    This page does two things:
    1. provide a javascript-generated picture of the box contents
    2. provide a tabular list of samples in the box
    """
    f = get_object_or_404(Freezer, pk=freezer_id)
    fname = f.__unicode__()
    c = getBoxContext(freezer_id, shelf_id, rack_id, drawer_id, box_id,
                      "#/swap-samples/")
    bn = get_box_name_or_empty_string(freezer_id, shelf_id, rack_id, drawer_id,
                                      box_id)
    c.update({
        'request': request,
        'fname': fname,
        'boxname': bn,
        'fid': freezer_id,
        'sid': shelf_id,
        'rid': rack_id,
        'did': drawer_id,
        'bid': box_id,
        'curr_samp': '0.1'
    })
    return render(request, 'freezers/rearrange_samples_within_box.html', c)

@login_required
def swap_samples(request, sample_id, cell_id):
    s = get_object_or_404(SampleLocation, pk=sample_id)
    fid = s.freezer.id
    ad = s.address
    sh, ra, dr, bo, ce = getposition(ad)
    redirect_url = '/freezers/%d/%d/%d/%d/%d/rearrange-samples/' % (fid,
                                                             sh, ra, dr, bo)
    address = ad >> 8
    addr = (address << 8) + int(cell_id)
    o = SampleLocation.objects.filter(freezer=fid,
                                      occupied=False, address=addr)
    if o.count() == 1:
        s.move(o[0])
    return HttpResponseRedirect(redirect_url)

@login_required
def remove_sample(request, sample_id):
    s = get_object_or_404(SampleLocation, pk=sample_id)
    fid = s.freezer.id
    ad = s.address
    sh, ra, dr, bo, ce = getposition(ad)
    redirect_url = '/freezers/%d/%d/%d/%d/%d/rearrange-samples/' % (fid,
                                                             sh, ra, dr, bo)
    name = s.name,
    aliquot = s.aliquot_number
    s.remove_sample()
    # Log when user removes samples
    log_action(
        request.user.username,
        "removed sample",
        {
            "sample_name": name,
            "aliquot_number": aliquot,
            "freezer_id": s.freezer.id,
            "address": hex(s.address)
        }
    )
    return HttpResponseRedirect(redirect_url)

@login_required
def select_samples_in_box(request, freezer_id, shelf_id, rack_id, drawer_id,
                          box_id):
    """
    This page does two things:
    1. provide a javascript-generated picture of the box contents
    2. provide a tabular list of samples in the box
    """
    f = get_object_or_404(Freezer, pk=freezer_id)
    fname = f.__unicode__()
    c = getBoxContext(freezer_id, shelf_id, rack_id, drawer_id, box_id,
                      "#/swap-samples/")
    bn = get_box_name_or_empty_string(freezer_id, shelf_id, rack_id, drawer_id,
                                      box_id)
    c.update({
        'request': request,
        'fname': fname,
        'boxname': bn,
        'fid': freezer_id,
        'sid': shelf_id,
        'rid': rack_id,
        'did': drawer_id,
        'bid': box_id,
        'curr_samp': '0.1'
    })
    return render(request, 'freezers/select_samples_in_box.html', c)

@login_required
def move_selected_samples_select_freezer(request):
    """
    Select a location to move sample into.
    First, select a freezer, then click a sublocation in the freezer
    """
    sample_query = request.GET.getlist('sample')
    query = 'sample=' + '&sample='.join(sample_query)
    redirect_to = request.GET.get('next', '/freezers/')
    if not sample_query:
        return HttpResponseRedirect(redirect_to)
    sample_ids = map(int, sample_query)
    samples = [get_object_or_404(SampleLocation, pk=s) for s in sample_ids]
    c = getMoveSampleDisplay(samples[0], samples)
    c.update({'request': request, 'query': query})
    if request.method == 'POST':
        form = MoveBoxForm(request.POST)
        if form.is_valid():
            freezer_id = form.cleaned_data['select_freezer'].id
            f = get_object_or_404(Freezer, pk=freezer_id)
            fname = f.__unicode__()
            shelves = freezerViewHelper(freezer_id)
            c.update({
                'form': form,
                'fid': freezer_id,
                'fname': fname,
                'shelves': shelves,
            })
            return render(request, 'freezers/move_sample_selection.html', c)
        c['form'] = form
    else:
        form = MoveBoxForm()
        c['form'] = form
    return render(request, 'freezers/move_sample_selection.html', c)

@login_required
def move_selection(request, freezer_id, shelf_id=None, rack_id=None,
                drawer_id=None, box_id=None, cell_id=None):
    """
    Moves the sample. If the user selects a box, show box contentents and
    allow user to select a cell to put the sample(s).
    Redirect user to location containing moved sample.
    """
    sample_query = request.GET.getlist('sample')
    sample_ids = map(int, sample_query)
    samples = [get_object_or_404(SampleLocation, pk=s) for s in sample_ids]
    query = 'sample=' + '&sample='.join(sample_query)
    if box_id and not cell_id:
        # Show user the selected box, prompt user to select a cell_ID
        f = get_object_or_404(Freezer, pk=freezer_id)
        c = getBoxContext(freezer_id, shelf_id, rack_id, drawer_id, box_id,
                          "", 'freezers/move-selected')
        bn = get_box_name_or_empty_string(freezer_id, shelf_id, rack_id,
                                          drawer_id, box_id)
        c.update(getMoveSampleDisplay(samples[0], samples))
        c.update({
            'request': request,
            'fname': f.__unicode__(),
            'boxname': bn,
            'fid': freezer_id,
            'sid': shelf_id,
            'rid': rack_id,
            'did': drawer_id,
            'bid': box_id,
            'curr_samp': '0.1',
            'query': query
        })
        return render(request, 'freezers/move_selection_in_box.html', c)
    containers = [c for c in (shelf_id, rack_id, drawer_id,
                              box_id, cell_id) if c]
    start_pos = [int(x or 1) for x in (shelf_id, rack_id, drawer_id, box_id,
                                       cell_id)]
    first_address = getaddress(start_pos)
    end_pos = list(start_pos)
    index = len(containers)-1 if containers else 0
    if index > 3:
        # If a cell is selected, the range should extend to the end of the box
        end_pos[3] += 1
        end_pos[4] = 1
    elif containers:
        end_pos[index] += 1
    else: # move to anywhere in freezer
        end_pos[index] += f.shelf_capacity
    end_address = getaddress(end_pos)
    fll = SampleLocation.objects.filter(freezer=freezer_id,
                                        occupied=False,
                                        address__gte=first_address,
                                        address__lt=end_address)
    n = len(samples)
    loc_list = getSampleList(0, fll, n)
    if not loc_list:
        f = get_object_or_404(Freezer, pk=freezer_id)
        fname = f.__unicode__()
        lname = " ".join([" ".join(p) for p in zip(
                                ("shelf rack drawer box".split(" ")),
                                (shelf_id, rack_id, drawer_id, box_id))])
        if cell_id:
            flobj = SampleLocation.objects.filter(freezer=freezer_id,
                                                  address=first_address)[0]
            if int(atoa):
                lname += " starting at"
            lname +=" cell %s" % flobj.cell_location_name()
        msg = "Error: Not enough room in %s %s. Please select another location" % (
                    fname, lname)
        form = MoveSampleForm()
        c = {'form': form, 'sid': sample_id, 'msg': msg}
        return render(request, 'freezers/move_sample.html', c)
    for i, samp in enumerate(samples):
        samp.move(loc_list[i])
    redirect_url = '/freezers/%s/' % freezer_id
    if len(containers) == 5:
        containers = containers[:4]
    for container in containers:
        redirect_url += container + '/'
    if not box_id:
        redirect_url += 'samples/'
    return HttpResponseRedirect(redirect_url)

@login_required
def remove_selected_samples(request):
    sample_query = request.GET.getlist('sample')
    redirect_url = request.GET.get('next', '/freezers/')
    log_dict = {}
    for i, sid in enumerate(sample_query):
        s = get_object_or_404(SampleLocation, pk=sid)
        log_dict["sample_%d_name" % i] = s.name
        log_dict["sample_%d_aliquot" % i] = s.aliquot_number
        log_dict["sample_%d_address" % i] = hex(s.address)
        s.remove_sample()
    # Log the deletion of samples
    log_action(
        request.user.username,
        "deleted samples",
        log_dict
    )
    return HttpResponseRedirect(redirect_url)

@login_required
def remodel_freezer(request, freezer_id, shelf_id, rack_id=None, drawer_id=None,
                    box_id=None):
    msg = ''
    if request.method == 'POST':
        form = ChangeFreezerLayout1(request.POST)
        if form.is_valid():
            new_box_width = form.cleaned_data['the_box_width_should_be']
            new_cell_capacity = form.cleaned_data['each_box_should_have']
            new_box_capacity = form.cleaned_data['each_drawer_should_have']
            new_drawer_capacity = form.cleaned_data['each_rack_should_have']
            new_rack_capacity = form.cleaned_data['each_shelf_should_have']

            args = [
                {'field_to_change': 'new_cell_capacity',
                 'new_value': new_cell_capacity, 'fid': freezer_id,
                 'sid': shelf_id, 'rid': rack_id, 'did': drawer_id,
                 'bid': box_id, 'box_dim': new_box_width},
                {'field_to_change': 'new_box_capacity',
                 'new_value': new_box_capacity, 'fid': freezer_id,
                 'sid': shelf_id, 'rid': rack_id, 'did': drawer_id},
                {'field_to_change': 'new_drawer_capacity',
                 'new_value': new_drawer_capacity,
                 'fid': freezer_id, 'sid': shelf_id, 'rid': rack_id},
                {'field_to_change': 'new_rack_capacity',
                 'new_value': new_rack_capacity, 'fid': freezer_id,
                 'sid': shelf_id},
            ]
            length = len([c for c in (rack_id, drawer_id,
                                      box_id) if c == None])
            for i in range(length+1):
                try:
                    remodelFreezerHelper(**args[i])
                except RemodelException, e:
                    msg = e
                    break
            if not msg:
                return HttpResponseRedirect(
                            '/freezers/%s/select-location/' % freezer_id)
    else:
        f = Freezer.objects.get(pk=freezer_id)
        d = {
            'each_shelf_should_have': f.rack_capacity,
            'each_rack_should_have': f.drawer_capacity,
            'each_drawer_should_have': f.box_capacity,
            'each_box_should_have': f.cell_capacity,
            'the_box_width_should_be': f.box_width
        }
        form = ChangeFreezerLayout1(d)
    c = {
        'request': request,
        'fid': freezer_id,
        'fname': Freezer.objects.get(pk=freezer_id).__unicode__(),
        'sid': shelf_id,
        'rid': rack_id,
        'did': drawer_id,
        'bid': box_id,
        'form': form
    }
    if msg:
        c['msg'] = msg
    return render(request, 'freezers/remodel_freezer1.html', c)

@login_required
def export_samples(request):
    """
    Allow users to export their sample info as tsv file
    """
    user = request.user
    exportSampleHelper(user)
    return HttpResponseRedirect('/freezers/home/%s/' % user.id)

@login_required
def delete_file(request, file_id):
    """
    Allow users to delete files
    """
    dirname = os.path.join(MEDIA_ROOT, request.user.username)
    filename = os.listdir(dirname)[int(file_id) - 1]
    os.remove(os.path.join(dirname, filename))
    return HttpResponseRedirect('/freezers/home/%s/' % request.user.id)

@login_required
def name_box(request, freezer_id, addr):
    """
    Allow users to name their boxes for easy id
    """
    box_name = request.GET.get('box_name', '')
    addr = int(addr)
    if box_name and request.is_ajax():
        try:
            bn = BoxName.objects.get(freezer=freezer_id, box_addr=addr)
            bn.name = box_name
            bn.save()
        except BoxName.DoesNotExist, e:
            f = Freezer.objects.get(pk=freezer_id)
            bn = BoxName(freezer=f, box_addr=addr, name=box_name)
            bn.save()
        return HttpResponse('success')
    return HttpResponseRedirect('/freezers/home/%s/' % request.user.id)

##############################################################################

@login_required
@transaction.autocommit
def remove_freezer(request, freezer_id):
    f = get_object_or_404(Freezer, pk=freezer_id)
    # move samples to 'Removed'
    locs = SampleLocation.objects.filter(freezer=freezer_id)
    s = locs.filter(occupied=True)
    # for logging
    num_samples = len(s)
    fname = f.__unicode__()
    # actually remove samples 
    [sample.remove_sample() for sample in s]
    # delete sample locations
    cur = connection.cursor()
    cur.execute("""DELETE FROM freezers_samplelocation WHERE freezer_id = %s""",
                (freezer_id,))
    # delete freezer
    f.delete()
    # Log when user removes freezer
    log_action(
        request.user.username,
        "removed freezer %s" % (freezer_id),
        {
            "freezer_name": fname,
            "affedted_samples": num_samples
        }
    )
    return HttpResponseRedirect('/freezers/')

@login_required
def show_box(request, freezer_id, address):
    s, r, d, b, c = getposition(int(address))
    return HttpResponseRedirect('/freezers/%s/%d/%d/%d/%d/' % (freezer_id, s, r, d, b))

@login_required
def remove_sample_from_index(request, sample_id):
    url = request.GET.get('next', '/freezers/samples/')
    s = get_object_or_404(SampleLocation, pk=sample_id)
    name = s.name
    aliquot = s.aliquot_number
    s.remove_sample()
    # Log when user removes samples
    log_action(
        request.user.username,
        "removed sample",
        {
            "sample_name": name,
            "aliquot_number": aliquot,
            "freezer_id": s.freezer.id,
            "address": hex(s.address)
        }
    )
    return HttpResponseRedirect(url)

@login_required
def return_removed_sample(request, removed_id):
    rs = get_object_or_404(RemovedSample, pk=removed_id)
    try:
        sl = SampleLocation.objects.get(freezer=rs.freezer.id, 
                                        address=rs.address)
    except:
        return HttpResponseRedirect('/freezers/removed/?return=dne&id=%s' % removed_id)
    if sl.occupied:
        return HttpResponseRedirect('/freezers/removed/?return=occ&id=%s' % removed_id)
    kwargs = {
        'name': rs.name,
        'sample_type': rs.sample_type,
        'user': rs.user,
        'pi_lab_supplier': rs.pi_lab_supplier,
        'date_added': rs.date_added,
        'production_date': rs.production_date,
        'concentration': rs.concentration,
        'volume': rs.volume,
        'aliquot_number': rs.aliquot_number,
        'solvent': rs.solvent,
        'species': rs.species,
        'host_cell_name': rs.host_cell_name,
        'catalog_number': rs.catalog_number,
        'comments': rs.comments
    }
    sl.addsample(**kwargs)
    fid = sl.freezer.id
    s, r, d, b, c = getposition(sl.address)
    rs.delete
    # Log when user returns samples
    log_action(
        request.user.username,
        "returned a removed sample to former location",
        {
            "sample_name": sl.name,
            "aliquot_number": sl.aliquot_number,
            "freezer_id": sl.freezer.id,
            "address": hex(sl.address)
        }
    )
    return HttpResponseRedirect('/freezers/%d/%d/%d/%d/%d/' % (fid, s, r, d, b))    
